"""JWT issuance/verification.

Backs the dev-login stub today; the `get_current_employee` dependency is the
single choke point every protected route relies on, so swapping in real
OIDC/SAML later only means changing how a token gets issued, not how it's
verified or consumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.employee_profile.models import EmployeeRole

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    employee_id: int
    role: EmployeeRole


def create_access_token(employee_id: int, role: EmployeeRole) -> str:
    """Issue a signed, short-lived JWT carrying employee_id and role claims."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(employee_id),
        "employee_id": employee_id,
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_employee(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """Resolve the calling employee from the bearer token.

    Every `employees/me/*` route depends on this instead of trusting any
    client-supplied employee id or role.
    """
    if credentials is None:
        raise AuthenticationError("Missing bearer token.")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    try:
        return CurrentUser(employee_id=int(payload["employee_id"]), role=EmployeeRole(payload["role"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Malformed token claims.") from exc
