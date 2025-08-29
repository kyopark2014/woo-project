import json
import logging
import sys
import os
import mcp_agent.utils as utils
import boto3
import re

from typing import Dict, List, Optional
from strands import Agent
from strands.models import BedrockModel
from botocore.config import Config
from strands_tools import memory, retrieve
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from typing import Dict, Optional, Any

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("mcp-basic")

index = 0
def add_notification(containers, message):
    global index
    if containers is not None:
        containers['notification'][index].info(message)
    index += 1

def add_response(containers, message):
    global index
    if containers is not None:
        containers['notification'][index].markdown(message)
    index += 1
    
status_msg = []
def get_status_msg(status):
    global status_msg
    status_msg.append(status)

    if status != "end)":
        status = " -> ".join(status_msg)
        return "[status]\n" + status + "..."
    else: 
        status = " -> ".join(status_msg)
        return "[status]\n" + status    

model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
aws_region = utils.bedrock_region

def get_model():
    STOP_SEQUENCE = "\n\nHuman:" 
    maxOutputTokens = 4096 # 4k

    # Bedrock client configuration
    bedrock_config = Config(
        read_timeout=900,
        connect_timeout=900,
        retries=dict(max_attempts=3, mode="adaptive"),
    )
    
    bedrock_client = boto3.client(
        'bedrock-runtime',
        region_name=aws_region,
        config=bedrock_config
    )

    model = BedrockModel(
        client=bedrock_client,
        model_id=model_id,
        max_tokens=maxOutputTokens,
        stop_sequences = [STOP_SEQUENCE],
        temperature = 0.1,
        top_p = 0.9,
        additional_request_fields={
            "thinking": {
                "type": "disabled"
            }
        }
    )
    return model

def load_mcp_config():
    config = None
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mcp.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return config

def isKorean(text):
    # check korean
    pattern_hangul = re.compile('[\u3131-\u3163\uac00-\ud7a3]+')
    word_kor = pattern_hangul.search(str(text))
    # print('word_kor: ', word_kor)

    if word_kor and word_kor != 'None':
        # logger.info(f"Korean: {word_kor}")
        return True
    else:
        # logger.info(f"Not Korean:: {word_kor}")
        return False

# Global variables
conversation_manager = SlidingWindowConversationManager(
    window_size=10,  
)
agent = None
knowledge_base_mcp_client = None
filesystem_client = None

def create_mcp_client(mcp_server_name: str):
    config = load_mcp_config()
    mcp_servers = config["mcpServers"]
    
    mcp_client = None
    for server_name, server_config in mcp_servers.items():
        logger.info(f"server_name: {server_name}")
        logger.info(f"server_config: {server_config}")   

        env = server_config["env"] if "env" in server_config else None

        if server_name == mcp_server_name:
            mcp_client = MCPClient(lambda: stdio_client(
                StdioServerParameters(
                    command=server_config["command"], 
                    args=server_config["args"], 
                    env=env
                )
            ))
            break
    
    return mcp_client

def initialize_agent(system_prompt=None):
    """Initialize the global agent with MCP client"""
    knowledge_base_mcp_client = create_mcp_client("knowledge_base")
    filesystem_client = create_mcp_client("filesystem")
        
    # Create agent within MCP client context manager
    with knowledge_base_mcp_client, filesystem_client:
        mcp_tools = knowledge_base_mcp_client.list_tools_sync()
        mcp_tools.extend(filesystem_client.list_tools_sync())
        logger.info(f"mcp_tools: {mcp_tools}")
        
        tools = []
        tools.extend(mcp_tools)

        tool_list = get_tool_list(tools)
        logger.info(f"tools loaded: {tool_list}")
    
        if system_prompt is None:
            system_prompt = (
                "당신의 이름은 현민이고, 질문에 대해 친절하게 답변하는 사려깊은 인공지능 도우미입니다."
                "상황에 맞는 구체적인 세부 정보를 충분히 제공합니다." 
                "모르는 질문을 받으면 솔직히 모른다고 말합니다."
            )
        model = get_model()

        agent = Agent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            conversation_manager=conversation_manager
        )
    
    return agent, knowledge_base_mcp_client, filesystem_client, tool_list

def get_tool_info(tool_name, tool_content):
    tool_references = []    
    urls = []
    content = ""

    try:
        if isinstance(tool_content, dict):
            json_data = tool_content
        elif isinstance(tool_content, list):
            json_data = tool_content
        else:
            json_data = json.loads(tool_content)
        
        logger.info(f"json_data: {json_data}")
        if isinstance(json_data, dict) and "path" in json_data:  # path
            path = json_data["path"]
            if isinstance(path, list):
                for url in path:
                    urls.append(url)
            else:
                urls.append(path)            

        for item in json_data:
            logger.info(f"item: {item}")
            if "reference" in item and "contents" in item:
                url = item["reference"]["url"]
                title = item["reference"]["title"]
                content_text = item["contents"][:200] + "..." if len(item["contents"]) > 200 else item["contents"]
                content_text = content_text.replace("\n", "")
                tool_references.append({
                    "url": url,
                    "title": title,
                    "content": content_text
                })
        logger.info(f"tool_references: {tool_references}")

    except json.JSONDecodeError:
        pass

    return content, urls, tool_references

def get_reference(references):
    ref = ""
    if references:
        ref = "\n\n### Reference\n"
        for i, reference in enumerate(references):
            ref += f"{i+1}. [{reference['title']}]({reference['url']}), {reference['content']}...\n"        
    return ref

def filter_mcp_parameters(tool_name, input_params):
    """Filter out unexpected parameters for MCP tools"""
    if not isinstance(input_params, dict):
        return input_params
    
    # Known problematic parameters that should be filtered out
    problematic_params = ['mcp-session-id', 'session-id', 'session_id']
    
    filtered_params = {}
    for key, value in input_params.items():
        if key not in problematic_params:
            filtered_params[key] = value
        else:
            logger.info(f"Filtered out problematic parameter '{key}' for tool '{tool_name}'")
    
    return filtered_params

async def show_streams(agent_stream, containers):
    tool_name = ""
    result = ""
    current_response = ""
    references = []

    async for event in agent_stream:
        # logger.info(f"event: {event}")
        if "message" in event:
            message = event["message"]
            logger.info(f"message: {message}")

            for content in message["content"]:      
                logger.info(f"content: {content}")          
                if "text" in content:
                    logger.info(f"text: {content['text']}")

                    if containers is not None:
                        add_response(containers, content['text'])

                    result = content['text']
                    current_response = ""

                if "toolUse" in content:
                    tool_use = content["toolUse"]
                    logger.info(f"tool_use: {tool_use}")
                    
                    tool_name = tool_use["name"]
                    input_params = tool_use["input"]
                    
                    # Filter out problematic parameters
                    filtered_input = filter_mcp_parameters(tool_name, input_params)
                    
                    logger.info(f"tool_name: {tool_name}, original_arg: {input_params}, filtered_arg: {filtered_input}")
                    
                    if containers is not None:       
                        add_notification(containers, f"tool name: {tool_name}, arg: {filtered_input}")
                        containers['status'].info(get_status_msg(f"{tool_name}"))
            
                refs = []
                if "toolResult" in content:
                    tool_result = content["toolResult"]
                    logger.info(f"tool_name: {tool_name}")
                    logger.info(f"tool_result: {tool_result}")
                    if "content" in tool_result:
                        tool_content = tool_result['content']
                        for content in tool_content:
                            if "text" in content:
                                if containers is not None:
                                    add_notification(containers, f"tool result: {content['text']}")

                                content, urls, refs = get_tool_info(tool_name, content['text'])
                                logger.info(f"content: {content}")
                                logger.info(f"urls: {urls}")
                                logger.info(f"refs: {refs}")

                                if refs:
                                    for r in refs:
                                        references.append(r)
                                        logger.info(f"refs: {refs}")

        if "data" in event:
            text_data = event["data"]
            current_response += text_data

            if containers is not None:
                containers["notification"][index].markdown(current_response)
            continue
        
    # get reference
    # result += get_reference(references)
    
    return result

def get_tool_list(tools):
    tool_list = []
    for tool in tools:
        if hasattr(tool, 'tool_name'):  # MCP tool
            tool_list.append(tool.tool_name)
        elif hasattr(tool, 'name'):  # MCP tool with name attribute
            tool_list.append(tool.name)
        elif hasattr(tool, '__name__'):  # Function or module
            tool_list.append(tool.__name__)
        elif str(tool).startswith("<module 'strands_tools."):   
            module_name = str(tool).split("'")[1].split('.')[-1]
            tool_list.append(module_name)
        else:
            # For MCP tools that might have different structure
            tool_str = str(tool)
            if 'MCPAgentTool' in tool_str:
                # Try to extract tool name from MCP tool
                try:
                    if hasattr(tool, 'tool'):
                        tool_list.append(tool.tool.name)
                    else:
                        tool_list.append(f"MCP_Tool_{len(tool_list)}")
                except:
                    tool_list.append(f"MCP_Tool_{len(tool_list)}")
            else:
                tool_list.append(str(tool))
    return tool_list

async def run_agent(query: str, containers: Optional[Dict[str, Any]] = None):
    global index, status_msg, agent, knowledge_base_mcp_client, filesystem_client
    index = 0
    status_msg = []
    tool_list = []
    
    if containers is not None:
        containers['status'].info(get_status_msg(f"(start"))  

    # Initialize agent if not exists
    if agent is None:
        agent, knowledge_base_mcp_client, filesystem_client, tool_list = initialize_agent(system_prompt=None)

    if containers is not None and tool_list:
        containers['tools'].info(f"tool_list: {tool_list}")
    
    # Use the global agent within MCP client context manager
    with knowledge_base_mcp_client, filesystem_client:
        agent_stream = agent.stream_async(query)
        result = await show_streams(agent_stream, containers)

    logger.info(f"result: {result}")

    if containers is not None:
        containers['status'].info(get_status_msg(f"end)"))

    return result

async def run_multi_agent(query: str, containers: Optional[Dict[str, Any]]=None):
    global index, status_msg
    index = 0
    status_msg = []
    
    if containers is not None:
        containers['status'].info(get_status_msg(f"(start"))  

    # create agent
    system_prompt = (
        "당신은 숙련된 QA 엔지니어입니다."
        "사용자가 전달한 파일을 로딩한 후에, 해당 문서의 API 항목만을 추출하세요."
        "API 항목에 <item> 태그를 추가하세요."
        "API 항목은 중복되지 않도록 추출하세요."
    )

    agent, knowledge_base_mcp_client, filesystem_client, tool_list = initialize_agent(system_prompt=system_prompt)

    if containers is not None:
        containers['status'].info(get_status_msg(f"extract_list"))  

    # if containers is not None and tool_list:
    #     containers['tools'].info(f"tool_list: {tool_list}")
    logger.info(f"tool_list: {tool_list}")

    with knowledge_base_mcp_client, filesystem_client:
        if containers is not None:
            add_response(containers, "## API 항목 추출 중...\n")
        
        agent_stream = agent.stream_async(query)
        result = await show_streams(agent_stream, containers)
        logger.info(f"results: {result}")
        
        # Extract API items from results and store in array
        api_items = []
        if result:
            # Convert result to string if needed
            results_text = str(result) if not isinstance(result, str) else result
            logger.info(f"results_text: {results_text}")
            
            # Split by <item> tags and extract content            
            # Find all <item> tags and their content, ensuring we don't include text before <item>
            item_pattern = r'<item>([^<]*(?:<[^/][^>]*>[^<]*</[^>]*>[^<]*)*)</item>'
            matches = re.findall(item_pattern, results_text, re.DOTALL)
            
            for match in matches:
                # Clean up the content (remove extra whitespace and newlines)
                cleaned_item = match.strip()
                if cleaned_item:
                    api_items.append(cleaned_item)
        
        logger.info(f"extracted api_items: {api_items}")
        logger.info(f"total api items found: {len(api_items)}")

    api_lists = "\n\n".join(api_items)

    # save api_items to file
    with open("api_items.txt", "w", encoding="utf-8") as f:
        f.write(api_lists)
    
    if containers is not None:
        add_response(containers, "## 추출된 항목\n" + api_lists)
    
    for i in range(2): # len(api_items)로 하면 전체를 추출할 수 있습니다. 편의상 3개만...
        if containers is not None:
            containers['status'].info(get_status_msg(f"extract_qa_details"))

        if containers is not None:
            add_notification(containers, f"{i+1}번째 API 항목에 대한 QA 항목을 추출합니다.")
        
        await extract_qa_details(query, i, api_items[i], containers)

    if containers is not None:
        containers['status'].info(get_status_msg(f"end)"))

    return api_lists

async def extract_qa_details(query: str, qa_index:int, api_item:str, containers: Optional[Dict[str, Any]]=None):
    global index, status_msg
    status_msg = []
    
    if containers is not None:
        containers['status'].info(get_status_msg(f"(qa_details"))  

    # create agent
    system_prompt = (
        "당신은 숙련된 QA 엔지니어입니다."
        "사용자가 전달한 파일을 로딩한 후에, 다음의 <item> tag에 있는 QA 항목을 test case로 작성해주세요."
        f"<item>{api_item}</item>" 
        "test case는 중복되지 않도록 작성해주세요."
        "답변은 한국어로 작성하세요."
    )

    agent, knowledge_base_mcp_client, filesystem_client, tool_list = initialize_agent(system_prompt=system_prompt)

    logger.info(f"tool_list: {tool_list}")

    with filesystem_client:
        if containers is not None:
            add_response(containers, f"# QA 항목 #{qa_index+1}\n")
        
        agent_stream = agent.stream_async(query)
        result = await show_streams(agent_stream, containers)
        logger.info(f"qa_detail: {result}")

    # save result to file
    with open(f"qa_details_{qa_index}.txt", "w", encoding="utf-8") as f:
        f.write(result)
    
    return result

    
