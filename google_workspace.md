# Google Workspace MCP

[MCP - Google Docs](https://github.com/kyopark2014/mcp/blob/main/google-docs.md)을 따라 Client ID와 Secret를 생성합니다. [mcp.json](./mcp_agent/mcp.json)에서 아래의 GOOGLE_OAUTH_CLIENT_ID와 GOOGLE_OAUTH_CLIENT_SECRET를 설정합니다.

```java
{
    "mcpServers": {
        "google_workspace": {
            "command": "uvx",
            "args": ["workspace-mcp"],
            "env": {
                "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret",
                "OAUTHLIB_INSECURE_TRANSPORT": "1"
            }
        }
    }
}
```

이제 Streamlit App을 실행합니다.

```text
streamlit run application/app.py
```

이후 Agent를 선택후 "Doc Search를 이용해 내 문서 정보를 알려주세요."라고 입력합니다.

<img width="1562" height="869" alt="image" src="https://github.com/user-attachments/assets/dcf56252-0d62-4817-bb5c-140170640ec0" />

이후 아래와 같이 search_docs를 이용해 Goolge Docs 문서를 가져와서 보여줍니다.

<img width="1019" height="782" alt="image" src="https://github.com/user-attachments/assets/3fe94292-0e1f-46b5-b9ef-6dedad0d7fd0" />
