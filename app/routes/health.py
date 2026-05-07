from flask import Blueprint, current_app

from app.utils.response import success_response

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    settings = current_app.extensions["settings"]
    return success_response(
        {
            "status": "ok",
            "service": "oce-mcp-server",
            "environment": settings.flask_env,
        }
    )
