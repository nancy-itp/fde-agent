"""Auth routes.

`dev-login` is a placeholder for the real IdP (OIDC/SAML) flow required by
`.claude/CLAUDE.md` §4/§6 for production. It issues a token for an existing,
active employee id with no password of any kind, and is hard-gated to the
`development` environment so it can never be reached in staging/production.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.schemas import DevLoginIn, TokenOut
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.security import create_access_token
from app.employee_profile import repository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=TokenOut)
def dev_login(payload: DevLoginIn, db: Session = Depends(get_db)) -> TokenOut:
    """Issue a token for an active employee id. Development environment only."""
    if settings.environment != "development":
        raise NotFoundError()

    employee = repository.get_active_employee(db, payload.employee_id)
    if employee is None:
        raise NotFoundError("No active employee with that id.")

    token = create_access_token(employee.employee_id, employee.role)
    return TokenOut(access_token=token)
