"""Typed exception classes caught once at the API boundary (see app.main)."""

from __future__ import annotations


class AppError(Exception):
    """Base for exceptions mapped to a safe, generic client-facing response.

    Never let an upstream error body or stack trace reach the client — raise
    one of these (or a subclass) with a message that's already safe to expose.
    """

    status_code: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class ValidationError(AppError):
    status_code = 422
    default_message = "The request was invalid."


class AuthenticationError(AppError):
    status_code = 401
    default_message = "Authentication failed."


class AuthorizationError(AppError):
    status_code = 403
    default_message = "You do not have access to this resource."


class NotFoundError(AppError):
    status_code = 404
    default_message = "The requested resource was not found."


class UpstreamIntegrationError(AppError):
    status_code = 502
    default_message = "An upstream service is currently unavailable."
