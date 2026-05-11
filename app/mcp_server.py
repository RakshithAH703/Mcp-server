import contextlib

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.config.settings import Settings
from app.services.consent_service import get_consent_service
from app.utils.errors import AppError
from app.utils.logging import configure_logging
from app.utils.logging import get_logger

settings = Settings.from_env()
configure_logging(settings.log_level)
logger = get_logger(__name__)

mcp = FastMCP(
    "onetrust-consent-mcp-server",
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def list_onetrust_purposes(search: str | None = None, page: int = 0, size: int = 50) -> dict:
    """List OneTrust consent purposes so an agent can choose a purpose ID for consent lookup."""
    return _execute_tool(
        "list_onetrust_purposes",
        lambda: get_consent_service(settings).list_purposes(search=search, page=page, size=size),
    )


@mcp.tool()
def list_onetrust_consents(
    purpose_id: str | None = None,
    purpose_name: str | None = None,
    purpose_name_contains: str | None = None,
    include_effective_status: bool = True,
    page: int = 0,
    size: int = 20,
) -> dict:
    """List OneTrust consent profiles for a selected purpose. Passing purpose_id is fastest."""
    return _execute_tool(
        "list_onetrust_consents",
        lambda: get_consent_service(settings).list_consents(
            purpose_id=purpose_id,
            purpose_name=purpose_name,
            purpose_name_contains=purpose_name_contains,
            include_effective_status=include_effective_status,
            page=page,
            size=size,
        ),
    )


def _execute_tool(tool_name: str, handler):
    try:
        return handler()
    except AppError as exc:
        logger.warning(
            "mcp_tool_failed",
            tool_name=tool_name,
            error_code=exc.code,
            error_message=exc.message,
        )
        raise ToolError(f"{exc.code}: {exc.message}") from exc


async def health_check(request):
    return JSONResponse(
        {
            "status": "ok",
            "service": "onetrust-consent-mcp-server",
            "environment": settings.environment,
            "mcp_endpoint": "/mcp",
        }
    )


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path != "/health" and settings.mcp_api_key:
            provided_key = request.headers.get("X-API-Key")
            if provided_key != settings.mcp_api_key:
                return JSONResponse(
                    {"error": "Invalid or missing MCP API key"},
                    status_code=403,
                )
        return await call_next(request)


@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
app.add_middleware(ApiKeyMiddleware)
if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id", "mcp-session-id"],
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
