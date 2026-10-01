"""Read-only diagnostic endpoint for the PRIO MCP connector.

Mirrors `app.main`'s unauthenticated `/health` liveness check — reports
connector reachability without touching employee/task data, so it carries
no row-level authorization concern per CLAUDE.md §4. This is the uptime
check for the PRIO integration called for by CLAUDE.md §8
("uptime/health checks per Core Application Service").
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.exceptions import UpstreamIntegrationError
from app.prio_integration import repository
from app.prio_integration.service import EXPECTED_STATUS_VOCABULARY_VERSION

router = APIRouter(prefix="/prio", tags=["prio_integration"])


@router.get("/health")
def prio_health() -> dict[str, str]:
    """Report whether the PRIO MCP connector can reach staging/production right now.

    Never raises — a health check's job is to report status, not error out.
    On failure, `detail` is always one of our own safe exception messages
    (never PRIO's raw error text), per `client.py`'s no-leak guarantee.
    """
    try:
        vocabulary = repository.get_status_vocabulary()
    except UpstreamIntegrationError as exc:
        return {"status": "unavailable", "detail": exc.message}

    status = "ok" if vocabulary.version == EXPECTED_STATUS_VOCABULARY_VERSION else "vocabulary_mismatch"
    return {"status": status, "status_vocabulary_version": vocabulary.version}
