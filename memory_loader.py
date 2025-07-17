import json
import logging
import sys
import os
import asyncio
import contextlib
import utils
import knowledge_base
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

def create_agent(system_prompt):
    if system_prompt==None:
        system_prompt = (
            "You are an experienced QA Engineer."
            "Provide sufficient specific details appropriate to the situation." 
            "If you don't know the answer to a question, honestly say you don't know."
        )

    model = get_model()
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[memory, retrieve]
    )
    
    return agent

def get_tool_list(tools):
    tool_list = []
    for tool in tools:
        if hasattr(tool, 'tool_name'):  # MCP tool
            tool_list.append(tool.tool_name)
                
        if str(tool).startswith("<module 'strands_tools."):   
            module_name = str(tool).split("'")[1].split('.')[-1]
            tool_list.append(module_name)
    return tool_list

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

async def loader():
    query = "9-2. 픽업필터 off일시"
    
    # create agent
    agent = create_agent(system_prompt=None)

    # memory
    # results = agent.tool.memory(
    #     action="retrieve",
    #     query=query,
    #     min_score=0.2,
    #     max_results=5,
    #     region="us-west-2",
    #     STRANDS_KNOWLEDGE_BASE_ID="YVYYTSJWDA"
    # )    
    # if "content" in results:
    #     content = results.get('content')
    #     for item in content:
    #         if "text" in item:
    #             text = item.get('text')            
    #             logger.info(f"text: {text}")

    # retrieve
    results = agent.tool.retrieve(
        text=query,
        numberOfResults=5,
        score=0.2,
        knowledgeBaseId="YVYYTSJWDA",
        region="us-west-2"
    )

    text = ""
    if "content" in results:
        content = results.get('content')
        for item in content:
            if "text" in item:
                text = item.get('text')            
                logger.info(f"text: {text}")

    prompt = f"Question: 아래의 context를 참조하여, {query}를 test하기 위한 test case를 작성해주세요.\n\n<context>{text}</context>"
    logger.info(f"prompt: {prompt}")

    agent_stream = agent.stream_async(prompt)
    result = await show_streams(agent_stream)

    logger.info(f"result: {result}")

    with open("test_case.md", "w", encoding="utf-8") as f:
         f.write(result)

if __name__ == "__main__":
    asyncio.run(loader())