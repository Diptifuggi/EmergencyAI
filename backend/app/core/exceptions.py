from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import traceback


class EmergencyIQBaseException(Exception):
    status_code: int = 400
    message: str = "An error occurred"

    def __init__(self, message: str | None = None, details: list | None = None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details or []


class DuplicateEmailError(EmergencyIQBaseException):
    status_code = 409
    message = "Email already exists"


class InvalidCredentialsError(EmergencyIQBaseException):
    status_code = 401
    message = "Invalid credentials"


class InactiveUserError(EmergencyIQBaseException):
    status_code = 403
    message = "User is inactive"


class InvalidTokenError(EmergencyIQBaseException):
    status_code = 401
    message = "Invalid or expired token"


class ResourceNotFoundError(EmergencyIQBaseException):
    status_code = 404
    message = "Resource not found"


class PermissionDeniedError(EmergencyIQBaseException):
    status_code = 403
    message = "Permission denied"


class FileTooLargeError(EmergencyIQBaseException):
    status_code = 413
    message = "Uploaded file is too large"


class InvalidFileTypeError(EmergencyIQBaseException):
    status_code = 422
    message = "Invalid file type"


class OllamaUnavailableError(EmergencyIQBaseException):
    status_code = 503
    message = "Ollama service is unavailable"


class PipelineStepFailedError(EmergencyIQBaseException):
    status_code = 500
    message = "Pipeline step failed"


def _emergencyiq_exception_handler(request: Request, exc: EmergencyIQBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.message, "details": exc.details},
    )


def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": True, "message": "Validation error", "details": exc.errors()},
    )


def generic_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "Internal server error", "details": [str(exc), tb]},
    )


def register_exception_handlers(app: FastAPI) -> None:
    # Specific app exceptions
    app.add_exception_handler(EmergencyIQBaseException, _emergencyiq_exception_handler)
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # Fallback
    app.add_exception_handler(Exception, generic_exception_handler)
