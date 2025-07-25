# Google Workspace MCP

[MCP - Google Docs](https://github.com/kyopark2014/mcp/blob/main/google-docs.md)을 따라 Client ID와 Secret를 생성합니다. [mcp.json](./mcp_agent/mcp.json)에서 아래와 같

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
``
