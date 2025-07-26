# Code Executior

여기에서는 AgentCore의 Code Executor를 이용한 Code 실행에 대해 설명합니다. 상세한 코드는 [code_executor.py](./code_executor.py)을 참조합니다.

아래와 같이 code를 실행하는 execute_python을 tool로 생성합니다.

```python
from bedrock_agentcore.tools.code_interpreter_client import code_session

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
```

이후 agent에서 아래와 같이 실행합니다.

```python
query = "strawberry의 r의 갯수는?"

response_text = ""
async for event in agent.stream_async(query):
    if "data" in event:
        chunk = event["data"]
        response_text += chunk
        print(chunk, end="")
```

## Reference

[Agent-Based Code Execution using Amazon AgentCore Bedrock Code Interpreter- Tutorial(Strands)](https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/05-AgentCore-tools/01-Agent-Core-code-interpreter/02-code-execution-with-agent-using-code-interpreter/strands-agent-code-execution-code-interpreter.ipynb)
