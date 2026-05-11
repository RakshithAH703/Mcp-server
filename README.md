# OneTrust Consent MCP Server

Official MCP Python SDK server for OneTrust consent and purpose lookup.

This project uses the official `mcp` Python SDK with `FastMCP` and Streamable HTTP transport. It is no longer a custom Flask-style MCP imitation.

```text
MCP Client / Agent
        -> Streamable HTTP MCP endpoint: /mcp
        -> FastMCP tools
        -> OneTrust OAuth + Consent APIs
```

## Tools

The server exposes these official MCP tools:

- `list_onetrust_purposes`
- `list_onetrust_consents`

Expected agent flow:

```text
1. Agent connects to /mcp
2. Agent runs MCP initialize
3. Agent runs tools/list
4. Agent calls list_onetrust_purposes
5. Agent chooses a purpose
6. Agent calls list_onetrust_consents with purpose_id, purpose_name, or purpose_name_contains
```

## Project Structure

```text
app/
  mcp_server.py              # Official FastMCP server and ASGI app
  config/
    settings.py              # .env configuration
  services/
    consent_service.py       # OneTrust purpose/consent business logic
    onetrust_client.py       # OneTrust API client with retries/timeouts
    onetrust_oauth.py        # OAuth2 client credentials token provider
  utils/
    errors.py
    logging.py
Dockerfile
docker-compose.yml
requirements.txt
run.py
```

## Environment

Keep local secrets in `.env`. Do not commit `.env`.

```env
APP_ENV=development
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

ONETRUST_BASE_URL=https://your-tenant.onetrust.com
ONETRUST_TOKEN_URL=https://your-tenant.onetrust.com/api/access/v1/oauth/token
ONETRUST_CLIENT_ID=your-client-id
ONETRUST_CLIENT_SECRET=your-client-secret
ONETRUST_SCOPE=
ONETRUST_TRUST_ENV_PROXY=false

# Optional. If set, MCP requests must include X-API-Key.
MCP_API_KEY=
```

## Run Locally

```powershell
cd C:\Users\rakshith.ah\One-Trust-Mco
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Server:

```text
http://localhost:8000
```

Health check:

```http
GET http://localhost:8000/health
```

Official MCP endpoint:

```text
http://localhost:8000/mcp
```

## Test With MCP Inspector

Start the server:

```powershell
python run.py
```

Then run MCP Inspector:

```powershell
npx -y @modelcontextprotocol/inspector
```

Connect to:

```text
http://localhost:8000/mcp
```

If `MCP_API_KEY` is configured, add this header in the client:

```http
X-API-Key: your-key
```

## Tool Inputs

`list_onetrust_purposes`

```json
{
  "page": 0,
  "size": 50
}
```

Optional `search` filters only the current page returned from OneTrust, so agents should page with `nextPage` until `last` is `true` when they need to inspect every purpose.

`list_onetrust_consents`

```json
{
  "purpose_id": "purpose-guid-from-list_onetrust_purposes",
  "include_effective_status": true,
  "page": 0,
  "size": 20
}
```

Name-based lookup is available, but `purpose_id` is recommended because it avoids extra OneTrust purpose scanning:

```json
{
  "purpose_name": "MCP-Steride",
  "page": 0,
  "size": 20
}
```

## Render Deployment

Deploy as a Render Web Service using Docker.

Set environment variables in Render dashboard, not in source control.

Docker runs:

```bash
uvicorn app.mcp_server:app --host 0.0.0.0 --port ${PORT:-8000}
```

After deployment:

```text
https://your-service.onrender.com/health
https://your-service.onrender.com/mcp
```

## Notes

- This is an official MCP SDK implementation using `mcp.server.fastmcp.FastMCP`.
- Streamable HTTP is served at `/mcp`.
- OneTrust credentials stay server-side.
- The browser/frontend should not store OneTrust credentials.
- For production, set `MCP_API_KEY` and require clients to send `X-API-Key`.
