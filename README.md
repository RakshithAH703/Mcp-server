# OneTrust Consent MCP Server

Standalone Flask-based MCP-style tool server for listing OneTrust consent and preference records. AI agents can initialize the server, discover available tools with JSON schemas, and invoke tools dynamically.

```text
AI Agent / n8n / Copilot / Claude / Custom LLM
        -> MCP HTTP endpoints
        -> OneTrust Consent MCP Server
        -> OneTrust Consent APIs
        -> structured tool result
```

This is not a REST CRUD proxy. The public interface is a tool protocol surface.

## Capabilities

- `POST /mcp/initialize`
- `GET /mcp/tools`
- `POST /mcp/tools/call`
- Dynamic tool discovery from `app/tools`
- JSON schema input validation for every tool
- OAuth2 client credentials flow for OneTrust
- Automatic bearer token reuse and refresh
- OneTrust retries, timeouts, and structured errors
- Structured JSON logging
- Docker and Docker Compose support
- Stateless runtime ready for future Redis/PostgreSQL integration

## Project Structure

```text
app/
  config/
    settings.py
  mcp/
    protocol.py
    registry.py
    schemas.py
  routes/
    health.py
    mcp_routes.py
  services/
    consent_service.py
    onetrust_client.py
    onetrust_oauth.py
  tools/
    get_hcp_consent.py
  utils/
    errors.py
    logging.py
    response.py
    security.py
    validation.py
Dockerfile
docker-compose.yml
requirements.txt
.env
run.py
```

## Tools

Active MCP tool for now:

- `list_onetrust_consents`

This repository is OneTrust-only. Previous CRM tool modules and services were removed.

Each tool defines:

- `name`
- `description`
- `inputSchema`
- Python execution handler

Tools are auto-registered from modules in `app/tools`. To add a new tool, create a new file with a `register(registry)` function and register a `ToolDefinition`.

## Environment

Keep your local configuration in `.env`.

Minimum OneTrust OAuth configuration for consent checks:

```env
ONETRUST_BASE_URL=https://your-tenant.onetrust.com
ONETRUST_TOKEN_URL=https://your-tenant.onetrust.com/api/access/v1/oauth/token
ONETRUST_CLIENT_ID=your-client-id
ONETRUST_CLIENT_SECRET=your-client-secret
ONETRUST_SCOPE=CONSENT_READ
ONETRUST_PURPOSE_NAME=
ONETRUST_PURPOSE_NAME_CONTAINS=mcp
ONETRUST_DEFAULT_PURPOSE_ID=
ONETRUST_TRUST_ENV_PROXY=false
```

Purpose resolution is dynamic. If `ONETRUST_PURPOSE_NAME` is set, the server finds that exact OneTrust purpose label/name. Otherwise it searches for purposes whose label/name contains `ONETRUST_PURPOSE_NAME_CONTAINS`, which defaults to `mcp`. If multiple purposes match, the server returns a clear configuration error instead of guessing. `ONETRUST_DEFAULT_PURPOSE_ID` is only a fallback for older deployments.

Do not use your personal OneTrust email/password in this server. Use them only to log in to the OneTrust UI and create/manage OAuth client credentials. The server should use OAuth client credentials with least-privilege scopes.

`MCP_API_KEY` is optional for local development. If set, callers must send:

```http
X-API-Key: your-key
```

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Server URL:

```text
http://localhost:8000
```

Health check:

```http
GET /health
```

## MCP Requests

### Initialize

```http
POST /mcp/initialize
```

Response:

```json
{
  "protocolVersion": "2024-11-05",
  "serverInfo": {
    "name": "onetrust-consent-mcp-server",
    "version": "1.0.0"
  },
  "capabilities": {
    "tools": {
      "listChanged": false
    }
  }
}
```

### List Tools

```http
GET /mcp/tools
```

Response:

```json
{
  "tools": [
    {
      "name": "list_onetrust_consents",
      "description": "List OneTrust consent and preference profiles.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "include_effective_status": {
            "type": "boolean",
            "default": true
          },
          "page": {
            "type": "integer",
            "minimum": 0,
            "default": 0
          },
          "size": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "default": 20
          }
        },
        "required": [],
        "additionalProperties": false
      }
    }
  ]
}
```

### Call Tool

```http
POST /mcp/tools/call
Content-Type: application/json
```

Request:

```json
{
  "tool": "list_onetrust_consents",
  "arguments": {
    "include_effective_status": true,
    "page": 0,
    "size": 20
  }
}
```

The caller does not need to send a purpose ID. The server dynamically resolves the OneTrust purpose and sends the resolved `purposeGuid` internally.

Response:

```json
{
  "tool": "list_onetrust_consents",
  "content": [
    {
      "type": "json",
      "json": {
        "items": []
      }
    }
  ],
  "isError": false
}
```

## Tool Mapping

The active OneTrust MCP tool calls `ConsentService`, which calls `OneTrustClient`.

```text
/mcp/tools/call
  -> ToolRegistry.call()
  -> app/tools/<tool>.py handler
  -> ConsentService
  -> OneTrustClient
  -> OneTrust Consent API
```

OneTrust purpose discovery path:

- `GET /api/consentmanager/v1/purposes`

OneTrust consent tool path:

- `GET /api/consentmanager/v1/datasubjects/profiles`

The tool resolves `purposeGuid` dynamically, then sends `purposeGuid`, `includeEffectiveStatus`, `properties=ignoreCount`, `page`, and `size`.

## Test With Postman

1. Start the server with `python run.py`.
2. Send `POST http://localhost:8000/mcp/initialize`.
3. Send `GET http://localhost:8000/mcp/tools`.
4. Send `POST http://localhost:8000/mcp/tools/call` with a tool request body.
5. If `MCP_API_KEY` is set, add `X-API-Key` to each MCP request.

## Docker

```powershell
docker compose up --build
```

The container reads `.env`, exposes port `8000`, and runs with Gunicorn.

Stop:

```powershell
docker compose down
```

## Deploy Later

Render/Railway:

- Connect GitHub repo.
- Use Docker deployment.
- Add all environment variables in the platform dashboard.
- Expose port from `$PORT` or `8000` depending on platform configuration.

AWS:

- Use ECS Fargate, App Runner, or Elastic Beanstalk.
- Store secrets in AWS Secrets Manager or SSM Parameter Store.
- Put the service behind HTTPS, API Gateway/ALB, and WAF if public.

## Security

- Do not commit `.env`.
- Keep OneTrust credentials only on the MCP server.
- Use OAuth2 client credentials for OneTrust; personal email/password should not be used for server API calls.
- Set `MCP_API_KEY` before public deployment.
- Use HTTPS in every deployed environment.
- Apply least-privilege OneTrust scopes.
- Avoid logging PHI/PII.
- Add rate limiting before external exposure.

## Future Scaling

- Redis for distributed OAuth token cache and rate limits.
- PostgreSQL for audit/event history if required.
- OpenTelemetry for traces across agent, MCP server, and OneTrust.
- More tool modules under `app/tools`.
- Contract tests with mocked OneTrust consent responses.
