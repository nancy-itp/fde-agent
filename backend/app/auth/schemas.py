"""Request/response schemas for the auth module."""

from __future__ import annotations

from pydantic import BaseModel


class DevLoginIn(BaseModel):
    employee_id: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
