"""Business logic for the Review Workflow service.

Not yet implemented. Per `docs/DEVELOPMENT_PLAN.md` Phase 5 (Days 21-25):
exception routing (default-deny to manager review on any confidence/
mismatch ambiguity, per CLAUDE.md's insecure-design control), approve/
edit/override endpoints with `role = manager` enforced server-side,
weighted overall-% computation on approval, and append-only audit logging
for every approval/override/mismatch resolution (actor, timestamp,
before/after) — the system of record per CLAUDE.md §7.
"""

from __future__ import annotations
