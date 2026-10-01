"""HTTP routes for the Review Workflow service.

Not yet implemented. Will carry the manager-facing approve/edit/override
endpoints (`role = manager` enforced server-side, never client-supplied,
per CLAUDE.md §4's broken-access-control control). Not wired into
`app.main` yet since there's no route to include.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/review", tags=["review_workflow"])
