from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class EmergencyIQBaseException(Exception):
    status_code: int = 500
    message: str = "An error occurred"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)

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
    message = "Ollama backend is unavailable"

class PipelineStepFailedError(EmergencyIQBaseException):
    status_code = 500
    message = "Pipeline step failed"


def _create_handler(status_code: int):
    async def _handler(request: Request, exc: EmergencyIQBaseException):
        return JSONResponse({"detail": exc.message}, status_code=status_code)
    return _handler


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DuplicateEmailError, _create_handler(DuplicateEmailError.status_code))
    app.add_exception_handler(InvalidCredentialsError, _create_handler(InvalidCredentialsError.status_code))
    app.add_exception_handler(InactiveUserError, _create_handler(InactiveUserError.status_code))
    app.add_exception_handler(InvalidTokenError, _create_handler(InvalidTokenError.status_code))
    app.add_exception_handler(ResourceNotFoundError, _create_handler(ResourceNotFoundError.status_code))
    app.add_exception_handler(PermissionDeniedError, _create_handler(PermissionDeniedError.status_code))
    app.add_exception_handler(FileTooLargeError, _create_handler(FileTooLargeError.status_code))
    app.add_exception_handler(InvalidFileTypeError, _create_handler(InvalidFileTypeError.status_code))
    app.add_exception_handler(OllamaUnavailableError, _create_handler(OllamaUnavailableError.status_code))
    app.add_exception_handler(PipelineStepFailedError, _create_handler(PipelineStepFailedError.status_code))
