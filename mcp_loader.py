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
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from contextlib import contextmanager
from strands import Agent
from strands.models import BedrockModel
from botocore.config import Config

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("mcp-basic")

def load_mcp_config():
    config = None
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mcp.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return config

class MCPClientManager:
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.client_configs: Dict[str, dict] = {}  # Store client configurations
        
    def add_client(self, name: str, command: str, args: List[str], env: dict[str, str] = {}) -> None:
        """Add a new MCP client configuration (lazy initialization)"""
        self.client_configs[name] = {
            "command": command,
            "args": args,
            "env": env
        }
        logger.info(f"Stored configuration for MCP client: {name}")
    
    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get or create MCP client (lazy initialization)"""
        if name not in self.client_configs:
            logger.warning(f"No configuration found for MCP client: {name}")
            return None
            
        if name not in self.clients:
            # Create client on first use
            config = self.client_configs[name]
            logger.info(f"Creating MCP client for {name} with config: {config}")
            try:
                self.clients[name] = MCPClient(lambda: stdio_client(
                    StdioServerParameters(
                        command=config["command"], 
                        args=config["args"], 
                        env=config["env"]
                    )
                ))
                logger.info(f"Successfully created MCP client: {name}")
            except Exception as e:
                logger.error(f"Failed to create MCP client {name}: {e}")
                logger.error(f"Exception type: {type(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
        else:
            logger.info(f"Reusing existing MCP client: {name}")
                
        return self.clients[name]
    
    def remove_client(self, name: str) -> None:
        """Remove an MCP client"""
        if name in self.clients:
            del self.clients[name]
        if name in self.client_configs:
            del self.client_configs[name]
    
    @contextmanager
    def get_active_clients(self, active_clients: List[str]):
        """Manage active clients context"""
        logger.info(f"active_clients: {active_clients}")
        active_contexts = []
        try:
            for client_name in active_clients:
                client = self.get_client(client_name)
                if client:
                    active_contexts.append(client)

            # logger.info(f"active_contexts: {active_contexts}")
            if active_contexts:
                with contextlib.ExitStack() as stack:
                    for client in active_contexts:
                        stack.enter_context(client)
                    yield
            else:
                yield
        except Exception as e:
            logger.error(f"Error in MCP client context: {e}")
            raise

# Initialize MCP client manager
mcp_manager = MCPClientManager()

def update_tools(mcp_servers: list):
    tools = []
    mcp_servers_loaded = 0
    for mcp_tool in mcp_servers:
        logger.info(f"Processing MCP tool: {mcp_tool}")        
        try:
            with mcp_manager.get_active_clients([mcp_tool]) as _:
                client = mcp_manager.get_client(mcp_tool)
                if client:
                    logger.info(f"Got client for {mcp_tool}, attempting to list tools...")
                    mcp_servers_list = client.list_tools_sync()
                    logger.info(f"{mcp_tool}_tools: {mcp_servers_list}")
                    if mcp_servers_list:
                        tools.extend(mcp_servers_list)
                        mcp_servers_loaded += 1
                        logger.info(f"Successfully added {len(mcp_servers_list)} tools from {mcp_tool}")
                    else:
                        logger.warning(f"No tools returned from {mcp_tool}")
                else:
                    logger.error(f"Failed to get client for {mcp_tool}")
        except Exception as e:
            logger.error(f"Error getting tools for {mcp_tool}: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            continue

    logger.info(f"Successfully loaded {mcp_servers_loaded} out of {len(mcp_servers)} MCP tools")
    logger.info(f"tools: {tools}")

    return tools

# Set up MCP clients
def init_mcp_clients(config: dict):
    if not config or "mcpServers" not in config:
        logger.warning(f"No configuration found")
        return

    logger.info(f"Initializing MCP clients")

    for server_key, server_config in config["mcpServers"].items():
        logger.info(f"server_key: {server_key}")

        if server_key:
            logger.info(f"server_config: {server_config}")
            
            name = server_key  
            command = server_config["command"]
            args = server_config["args"]
            env = server_config.get("env", {})  # Use empty dict if env is not present                
            logger.info(f"Adding MCP client - name: {name}, command: {command}, args: {args}, env: {env}")        

            try:
                mcp_manager.add_client(name, command, args, env)
                logger.info(f"Successfully added MCP client for {name}")
            except Exception as e:
                logger.error(f"Failed to add MCP client for {name}: {e}")
                continue

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

def create_agent(system_prompt, tools):
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
        tools=tools
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

async def show_streams(agent_stream):
    tool_name = ""
    result = ""
    current_response = ""

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
            
                if "toolResult" in content:
                    tool_result = content["toolResult"]
                    logger.info(f"tool_name: {tool_name}")
                    # logger.info(f"tool_result: {tool_result}")
                    if "content" in tool_result:
                        tool_content = tool_result["content"]
                        logger.info(f"tool_content: {tool_content}")

        if "data" in event:
            text_data = event["data"]
            current_response += text_data
            continue
    
    return result

async def loader():
    config = load_mcp_config()
    logger.info(f"config: {config}")

    query = "9-2. 픽업필터 off일시"

    # initialize mcp clients
    init_mcp_clients(config)

    # load tools
    mcp_servers = ["knowledge_base_lambda", "awslabs.aws-documentation-mcp-server"]
    tools = update_tools(mcp_servers)
    tool_list = get_tool_list(tools)
    logger.info(f"tool_list: {tool_list}")

    # run agent
    agent = create_agent(system_prompt=None, tools=tools)
    with mcp_manager.get_active_clients(mcp_servers) as _:
        agent_stream = agent.stream_async(f"KnowledgeBase를 이용해 {query}에 대한 정보를 조회하고, test하기 위한 test case를 작성해주세요.")

        result = await show_streams(agent_stream)

        # save result to file
        with open("test_case.md", "w", encoding="utf-8") as f:
            f.write(result)

    logger.info(f"result: {result}")    
    
if __name__ == "__main__":
    asyncio.run(loader())