from functools import wraps

from flask import current_app, request

from app.utils.errors import AuthorizationError


def require_api_key(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        settings = current_app.extensions["settings"]
        if not settings.mcp_api_key:
            return handler(*args, **kwargs)

        provided_key = request.headers.get("X-API-Key")
        if provided_key != settings.mcp_api_key:
            raise AuthorizationError("Invalid or missing MCP API key")
        return handler(*args, **kwargs)

    return wrapper
