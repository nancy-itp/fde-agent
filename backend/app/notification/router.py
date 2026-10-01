"""HTTP routes for the Notification Service.

Not yet implemented. Likely no public routes at all — sends are triggered
internally by `scheduler`/`review_workflow`, not requested over HTTP. This
file exists for structural consistency (CLAUDE.md §2). Not wired into
`app.main` yet since there's no route to include.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/notification", tags=["notification"])
