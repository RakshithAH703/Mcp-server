class AppError(Exception):
    code = "internal_error"

    def __init__(self, message: str, *, details: dict | list | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class AuthenticationError(AppError):
    code = "authentication_error"


class AuthorizationError(AppError):
    code = "authorization_error"


class BadRequestError(AppError):
    code = "bad_request"


class CrmApiError(AppError):
    code = "crm_api_error"


class CrmUnavailableError(AppError):
    code = "crm_unavailable"
