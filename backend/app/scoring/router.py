"""HTTP routes for the Scoring service.

Not yet implemented. Scoring runs are expected to be triggered internally
by `scheduler`, not via a public endpoint — this file exists for structural
consistency (CLAUDE.md §2) and may end up with only an internal/manual
"rerun this employee's cycle" admin route, not a general-purpose API
surface. Not wired into `app.main` yet since there's no route to include.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/scoring", tags=["scoring"])
