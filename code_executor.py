from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands import Agent, tool
import json
import asyncio
from typing import Dict, Any, List

SYSTEM_PROMPT = """You are a helpful AI assistant that validates all answers through code execution.

VALIDATION PRINCIPLES:
1. When making claims about code, algorithms, or calculations - write code to verify them
2. Use execute_python to test mathematical calculations, algorithms, and logic
3. Create test scripts to validate your understanding before giving answers
4. Always show your work with actual code execution
5. If uncertain, explicitly state limitations and validate what you can

APPROACH:
- If asked about a programming concept, implement it in code to demonstrate
- If asked for calculations, compute them programmatically AND show the code
- If implementing algorithms, include test cases to prove correctness
- Document your validation process for transparency
- The sandbox maintains state between executions, so you can refer to previous results

TOOL AVAILABLE:
- execute_python: Run Python code and see output

RESPONSE FORMAT: The execute_python tool returns a JSON response with:
- sessionId: The sandbox session ID
- id: Request ID
- isError: Boolean indicating if there was an error
- content: Array of content objects with type and text/data
- structuredContent: For code execution, includes stdout, stderr, exitCode, executionTime"""

@tool
def execute_python(code: str, description: str = "") -> str:
    """Execute Python code in the sandbox."""
    
    if description:
        code = f"# {description}\n{code}"
    
    print(f"\n Generated Code: {code}")
    
    with code_session("us-west-2") as code_client:
        response = code_client.invoke("executeCode", {
            "code": code,
            "language": "python",
            "clearContext": False
        })
    
    for event in response["stream"]:
        return json.dumps(event["result"])
    
agent = Agent(
    tools=[execute_python],
    system_prompt=SYSTEM_PROMPT,
    callback_handler=None
)

async def main():
    query = "strawberry의 r의 갯수는?"

    try:
        response_text = ""
        async for event in agent.stream_async(query):
            if "data" in event:
                chunk = event["data"]
                response_text += chunk
                print(chunk, end="")
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
