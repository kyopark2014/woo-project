# Woo Project

이 프로젝트는 RAG를 이용해 조회한 문서에서 Text Case를 추출하는 예제입니다.

## Architecture

## 주요 구현

### 모델 정보의 확인

```python
def get_model():
    STOP_SEQUENCE = "\n\nHuman:" 
    maxOutputTokens = 4096 # 4k

    bedrock_config = Config(
        read_timeout=900,
        connect_timeout=900,
        retries=dict(max_attempts=3, mode="adaptive"),
    )

    import boto3
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


## 실행 결과

Terminal에서 아래와 같이 실행합니다.

```text
python mcp_loader.py
```

이 python에서는 아래와 같은 작업을 수행합니다.

```python
query = "9-2. 픽업필터 off일시"

agent_stream = agent.stream_async(f"KnowledgeBase를 이용해 {query}에 대한 정보를 조회하고, test하기 위한 test case를 작성해주세요.")

result = await show_streams(agent_stream)
```

실행한 결과는 [test_case.md](./test_case.md)에서 확인할 수 있습니다. 이 결과의 일부는 아래와 같이 확인이 가능합니다.

<img width="651" height="780" alt="image" src="https://github.com/user-attachments/assets/32e1e792-2e4b-49da-9c1c-09bcf3265f49" />
