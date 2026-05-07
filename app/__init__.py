import time
import uuid

import structlog
from flask import Flask, g, request

from app.config.settings import Settings
from app.routes.health import health_bp
from app.routes.mcp_routes import mcp_bp
from app.mcp.registry import discover_tools
from app.utils.errors import register_error_handlers
from app.utils.logging import configure_logging


def create_app() -> Flask:
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    app = Flask(__name__)
    app.config.from_mapping(settings.to_flask_config())
    app.extensions["settings"] = settings
    app.extensions["tool_registry"] = discover_tools()

    register_error_handlers(app)
    register_request_logging(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(mcp_bp, url_prefix="/mcp")

    return app


def register_request_logging(app: Flask) -> None:
    logger = structlog.get_logger(__name__)

    @app.before_request
    def bind_request_context():
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.request_id = request_id
        g.request_started_at = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.path,
        )

    @app.after_request
    def log_response(response):
        elapsed_ms = round((time.perf_counter() - g.request_started_at) * 1000, 2)
        response.headers["X-Request-ID"] = g.request_id
        logger.info("request_completed", status_code=response.status_code, elapsed_ms=elapsed_ms)
        structlog.contextvars.clear_contextvars()
        return response
