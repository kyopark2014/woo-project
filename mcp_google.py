import json
import logging
import sys
import os
import asyncio
import contextlib
import utils
import boto3

from typing import Dict, List, Optional
from strands import Agent
from strands.models import BedrockModel
from botocore.config import Config
from strands_tools import memory, retrieve

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("mcp-basic")

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

def create_agent(system_prompt):    
    # google workspace
    from strands.tools.mcp import MCPClient
    from mcp import stdio_client, StdioServerParameters

    config = load_mcp_config()
    logger.info(f"config: {config}")

    mcp_servers = config["mcpServers"]
    google_mcp_client = None
    for server_name, server_config in mcp_servers.items():
        logger.info(f"server_name: {server_name}")
        logger.info(f"server_config: {server_config}")
        if server_name == "google_workspace":
            google_mcp_client = MCPClient(lambda: stdio_client(
                StdioServerParameters(
                    command=server_config["command"], 
                    args=server_config["args"], 
                    env=server_config["env"]
                )
            ))
            break

    with google_mcp_client as client:
        google_tools = client.list_tools_sync()

        tools = [retrieve] + google_tools
        
        tool_list = get_tool_list(google_tools)
        logger.info(f"Google Workspace tools loaded: {len(tool_list)} tools")
        logger.info(f"Tool categories: Gmail({len([t for t in tool_list if 'gmail' in t.lower()])}), Drive({len([t for t in tool_list if 'drive' in t.lower()])}), Calendar({len([t for t in tool_list if 'event' in t.lower() or 'calendar' in t.lower()])}), Docs({len([t for t in tool_list if 'doc' in t.lower()])}), Sheets({len([t for t in tool_list if 'sheet' in t.lower() or 'spreadsheet' in t.lower()])}), Chat({len([t for t in tool_list if 'chat' in t.lower() or 'message' in t.lower()])}), Forms({len([t for t in tool_list if 'form' in t.lower()])}), Slides({len([t for t in tool_list if 'presentation' in t.lower() or 'slide' in t.lower()])}), Tasks({len([t for t in tool_list if 'task' in t.lower()])})")
        
        # system prompt
        if system_prompt is None:
            system_prompt = (
                "당신의 이름은 서연이고, 질문에 대해 친절하게 답변하는 사려깊은 인공지능 도우미입니다."
                "상황에 맞는 구체적인 세부 정보를 충분히 제공합니다." 
                "모르는 질문을 받으면 솔직히 모른다고 말합니다."            
            )

        model = get_model()
        agent = Agent(
            model=model,
            system_prompt=system_prompt,
            tools=tools
        )
    
    return agent

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

async def show_streams(agent_stream):
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

                    result = content['text']
                    current_response = ""

                if "toolUse" in content:
                    tool_use = content["toolUse"]
                    logger.info(f"tool_use: {tool_use}")
                    
                    tool_name = tool_use["name"]
                    input = tool_use["input"]
                    
                    logger.info(f"tool_nmae: {tool_name}, arg: {input}")
            
                refs = []
                if "toolResult" in content:
                    tool_result = content["toolResult"]
                    logger.info(f"tool_name: {tool_name}")
                    logger.info(f"tool_result: {tool_result}")
                    if "content" in tool_result:
                        tool_content = tool_result['content']
                        for content in tool_content:
                            if "text" in content:
                                content, urls, refs = get_tool_info(tool_name, content['text'])
                                for r in refs:
                                    references.append(r)
                                    logger.info(f"refs: {r}")

        if "data" in event:
            text_data = event["data"]
            current_response += text_data
            continue
        
    # get reference
    result += get_reference(references)
    
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

async def mcp_google():
    query = "내 Google Docs의 문서 리스트는?"
    
    # create agent
    agent = create_agent(system_prompt=None)

    agent_stream = agent.stream_async(query)
    result = await show_streams(agent_stream)

    logger.info(f"result: {result}")

    with open("test_case.md", "w", encoding="utf-8") as f:
         f.write(result)

if __name__ == "__main__":
    asyncio.run(mcp_google())