import logging
import sys
import qa_agent.agent as agent

from typing import Dict, Optional, Any
from mcp.server.fastmcp import FastMCP 

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("rag")

try:
    mcp = FastMCP(
        name = "qa_agent",
        instructions=(
            "You are a helpful qa assistant. "
            "You generate test cases for given requirements."
        ),
    )
    logger.info("MCP server initialized successfully")
except Exception as e:
        err_msg = f"Error: {str(e)}"
        logger.info(f"{err_msg}")

######################################
# QA Agent
######################################
@mcp.tool()
async def generate_test_cases(subject: str) -> list:
    """
    Generate test cases for given requirements.
    subject: the subject to generate test cases
    return: the test cases
    """
    logger.info(f"subject: {subject}")

    result = await agent.run_agent(subject)
    logger.info(f"result: {result}")
    return result

if __name__ =="__main__":
    print(f"###### main ######")
    mcp.run(transport="stdio")
