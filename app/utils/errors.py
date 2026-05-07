from http import HTTPStatus

from flask import Flask, jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from app.utils.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    code = "internal_error"

    def __init__(self, message: str, *, details: dict | list | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class AuthenticationError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "authentication_error"


class AuthorizationError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "authorization_error"


class BadRequestError(AppError):
    status_code = HTTPStatus.BAD_REQUEST
    code = "bad_request"


class CrmApiError(AppError):
    status_code = HTTPStatus.BAD_GATEWAY
    code = "crm_api_error"


class CrmUnavailableError(AppError):
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    code = "crm_unavailable"


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        logger.warning(
            "application_error",
            path=request.path,
            code=error.code,
            status_code=int(error.status_code),
            details=error.details,
        )
        return _error_response(error.code, error.message, error.status_code, error.details)

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        details = error.errors()
        return _error_response("validation_error", "Request validation failed", HTTPStatus.BAD_REQUEST, details)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        return _error_response("http_error", error.description, HTTPStatus(error.code or 500))

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception("unexpected_error", path=request.path, error=str(error))
        return _error_response(
            "internal_error",
            "An unexpected error occurred",
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )


def _error_response(code: str, message: str, status: HTTPStatus, details=None):
    body = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        body["error"]["details"] = details
    return jsonify(body), int(status)
