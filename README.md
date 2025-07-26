# Woo Project

이 프로젝트는 Test Case를 생성하기 위해 MCP로 구현된 RAG를 활용합니다. 생성할 Test Case에 대해 RAG를 조회한 후에 얻어진 문서에서 Test Case를 추출합니다. 또한 여기에서는 multi step reasoning이 우수한 [Strands Agent](https://github.com/kyopark2014/strands-agent)를 활용합니다. 

## Architecture

여기서 구현하려는 전체 Architecture는 아래와 같습니다. EC2에 application과 MCP를 올리고 CloudFront와 ALB를 이용해 안전하게 외부와 연결합니다. 생성된 결과물이나 RAG 문서를 공유할 때에는 S3에 파일을 올리고 CloudFront를 이용해 제공합니다. 또한 Bedrock Knowledge Base를 이용해 RAG를 구성합니다. RAG에 넣을 문서는 S3와 동기화를 통해 chunking을 수행하고 관련된 문서로 활용합니다. 필요시 AWS Document의 문서를 MCP를 이용해 활용할 수 있습니다. 

<img width="597" height="362" alt="image" src="https://github.com/user-attachments/assets/ca3f4103-3b92-4154-84dd-b1ecfbffe9e2" />

## 주요 구현

### 모델 정보의 확인

여기에서는 Anthropic Claude 3.7을 사용합니다. 목적에 맞게 적절한 모델을 선택할 수 있습니다.

```python
import boto3
model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

def get_model():
    STOP_SEQUENCE = "\n\nHuman:" 
    maxOutputTokens = 4096 # 4k

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
```

### MCP 서버의 설정

여기에서는 [mcp.json](./mcp.json)에서 MCP 서버의 정보를 가져옵니다. 아래는 mcp.json의 예입니다. knowledge_base_lambda는 lambda를 이용해 knowledge base를 조회합니다. awslabs.aws-documentation-mcp-server는 AWS document의 문서를 조회하는 MCP 서버입니다.

```java
{
    "mcpServers": {
        "knowledge_base_lambda": {
            "command": "python",
            "args": [
                "mcp_server_lambda_knowledge_base.py"
            ]
        },
        "awslabs.aws-documentation-mcp-server": {
            "command": "uvx",
            "args": ["awslabs.aws-documentation-mcp-server@latest"],
            "env": {
                "FASTMCP_LOG_LEVEL": "ERROR"
            }
        }
    }
}
```

mcp.json에서 mcpServers의 정보를 가져와서 client로 등록합니다.

```python
def init_mcp_clients(config: dict):
    for server_key, server_config in config["mcpServers"].items():
        name = server_key  
        command = server_config["command"]
        args = server_config["args"]
        env = server_config.get("env", {})  # Use empty dict if env is not present                
        mcp_manager.add_client(name, command, args, env)
```

아래와 같이 사용할 MCP 서버를 지정하고 tool의 정보를 조회합니다.

```python
mcp_servers = ["knowledge_base_lambda", "awslabs.aws-documentation-mcp-server"]
tools = update_tools(mcp_servers)

tool_list = get_tool_list(tools)
logger.info(f"tool_list: {tool_list}")

def update_tools(mcp_servers: list):
    tools = []
    mcp_servers_loaded = 0
    for mcp_tool in mcp_servers:
        with mcp_manager.get_active_clients([mcp_tool]) as _:
            client = mcp_manager.get_client(mcp_tool)
            if client:
                mcp_servers_list = client.list_tools_sync()
                if mcp_servers_list:
                    tools.extend(mcp_servers_list)
                    mcp_servers_loaded += 1
            else:
                logger.error(f"Failed to get client for {mcp_tool}")
    return tools
```

Strands agent를 생성합니다.

```python
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
```

아래와 같이 agent를 실행하여 결과를 얻습니다. 

```python
agent = create_agent(system_prompt=None, tools=tools)
with mcp_manager.get_active_clients(mcp_servers) as _:
    agent_stream = agent.stream_async(f"KnowledgeBase를 이용해 {query}에 대한 정보를 조회하고, test하기 위한 test case를 작성해주세요.")
    result = await show_streams(agent_stream)
    # save result to file
    with open("test_case.md", "w", encoding="utf-8") as f:
        f.write(result)
```

### Strands Tool로 Knowledge Base 활용하기

Strands의 retrive를 이용해 Knolwledge Base를 이용해 구성한 RAG로 부터 필요한 문서를 조회할 수 있습니다. 상세한 코드는 [memory_loader.py](https://github.com/kyopark2014/woo-project/blob/main/memory_loader.py)을 참조하기 바랍니다.

```python
from strands_tools import retrieve
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
```

## 실행 준비

### 환경 준비

여기에서는 S3, CloudFront, OpenSearch (Serverless), Bedrock Knowledge Base를 활용합니다. 이를 위한 상세 내용은 [cdk-woo-project-stack.ts](./cdk-woo-project/lib/cdk-woo-project-stack.ts)을 참조합니다. 이를 인프라로 배포할 때에는 아래와 같이 수행합니다.

먼저, cdk-woo-project로 이동하여 CDK 환경설정을 준비합니다. 만약 한번도 bootstrapping을 하지 않았다면, [AWS CDK 부트스트래핑](https://docs.aws.amazon.com/ko_kr/cdk/v2/guide/bootstrapping.html)을 참조하여 수행합니다.

- Bootstrapping

여기서 account-id를 확인하여 아래의 "123456789012"을 바꾼후 실행합니다.

```text
cdk bootstrap aws://123456789012/us-west-2
```

- CDK 배포

```text
cd cdk-woo-project && npm install
cdk deploy --require-approval never --all
```

배포가 완료되면 아래와 같은 Output 파일에서 CdkWooProjectStack.environmentforwooproject을 복사하여 [config.json](./config.json)을 업데이트 합니다.

<img width="1047" height="141" alt="image" src="https://github.com/user-attachments/assets/c76ae1f4-f612-4e6e-b755-3e3cbacdbd53" />


### 문서 동기화 하기 

Knowledge Base에서 문서를 활용하기 위해서는 S3에 문서 등록 및 동기화기 필요합니다. 

여기에서는 테스트를 위해 "실제사례/실제사례1/searchplatform-[Phase1] 4월8일 오픈타겟 검색지면 포장 대응-270625-100949.pdf"를 활용하고자 합니다. [S3 Console](https://us-west-2.console.aws.amazon.com/s3/home?region=us-west-2)에 접속하여 "storage-for-woo-project-xxxxxxxxxxxx-us-west-2"를 선택하고, 아래와 같이 docs폴더를 생성한 후에 파일을 업로드 합니다. 

<img width="400" alt="image" src="https://github.com/user-attachments/assets/482f635e-a38d-4525-b9a3-fb1c2a9089c8" />

이후 [Knowledge Bases Console](https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/knowledge-bases)에 접속하여, "woo-project"라는 Knowledge Base를 선택합니다. 이후 아래와 같이 [Sync]를 선택합니다.

<img width="1533" height="287" alt="noname" src="https://github.com/user-attachments/assets/2edd3b6b-dbce-4784-b640-139fa84cc223" />


### Google Workspace

[google_workspace.md](https://github.com/kyopark2014/woo-project/blob/main/google_workspace.md)에서는 Google Docs등을 활용하기 위해 google workspace를 MCP로 등록하는 방법에 대해 설명합니다.

### Code 실행하기

[code-executor.md](https://github.com/kyopark2014/woo-project/blob/main/code-executor.md)에서는 AgentCore의 code interpreter를 이용해 code를 실행하는 것을 설명합니다.


### 실행하기 

Terminal을 열고 github 주소로 이동한 후에 아래와 같이 실행합니다.

```text
python mcp_loader.py
```

이 python에서는 아래와 같은 작업을 수행합니다.

```python
query = "9-2. 픽업필터 off일시"

agent_stream = agent.stream_async(f"KnowledgeBase를 이용해 {query}에 대한 정보를 조회하고, test하기 위한 test case를 작성해주세요.")

result = await show_streams(agent_stream)
```

원하는 목적에 맞게 query를 바꿔서 수행합니다.


### 실행 결과


실행한 결과의 한 예는 [9_2_test_case.md](./9_2_test_case.md)와 같습니다. 이 결과의 일부는 아래와 같습니다.

<img width="651" height="780" alt="image" src="https://github.com/user-attachments/assets/32e1e792-2e4b-49da-9c1c-09bcf3265f49" />

## Reference

[Strands Agents와 오픈 소스 AI 에이전트 SDK 살펴보기](https://aws.amazon.com/ko/blogs/tech/introducing-strands-agents-an-open-source-ai-agents-sdk/)

[Streamlit으로 구현한 Strands Agent](https://github.com/kyopark2014/strands-agent)

[Strands Agents SDK](https://strandsagents.com/0.1.x/)

[Strands Agents Samples](https://github.com/strands-agents/samples/tree/main)

[Example Built-in Tools](https://strandsagents.com/0.1.x/user-guide/concepts/tools/example-tools-package/)

[Introducing Strands Agents, an Open Source AI Agents SDK](https://aws.amazon.com/ko/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/)

[use_aws.py](https://github.com/strands-agents/tools/blob/main/src/strands_tools/use_aws.py)

[Strands Agents와 오픈 소스 AI 에이전트 SDK 살펴보기](https://aws.amazon.com/ko/blogs/tech/introducing-strands-agents-an-open-source-ai-agents-sdk/)

[Drug Discovery Agent based on Amazon Bedrock](https://github.com/hsr87/drug-discovery-agent)

[Strands Agent - Swarm](https://strandsagents.com/latest/user-guide/concepts/multi-agent/swarm/)
