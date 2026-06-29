"""Domain exceptions.

Services raise these; a single handler in `main.py` maps them to HTTP
responses. Keeps routers and services free of FastAPI HTTP details.
"""

from __future__ import annotations


class AppError(Exception):
    status_code = 400
    code = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status_code = 400
    code = "invalid_request"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
