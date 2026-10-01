"""HTTP routes for the Scheduler service.

Not yet implemented. Per CLAUDE.md §5, the eventual biweekly trigger
endpoint needs rate limiting/abuse protection and autoscaling limits so it
can't be used to flood compute — build that in from the start rather than
retrofitting it once a route exists. Not wired into `app.main` yet since
there's no route to include.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
