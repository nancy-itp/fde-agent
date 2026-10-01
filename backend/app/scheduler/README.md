# Scheduler

**Status**: skeleton only (`models.py` is real; `router.py`/`service.py`/
`repository.py` are documented placeholders). Built in
`docs/DEVELOPMENT_PLAN.md` Phase 8, Day 40.

## Responsibility

Owns the biweekly review-cycle cadence: `ReviewCycle` (`models.py`) — the
cycle records every other service's cycle-scoped data (self-reports,
snapshots, scores, mismatch flags, API call logs) foreign-keys against.

Drives the cycle per `docs/ARCHITECTURE.md`: profile-update reminders on
day 1 (via `notification`), continuous/nightly `prio_integration` sync
through the cycle, triggering `scoring` once both a profile update and a
fresh tracker snapshot exist for an employee — batched across everyone due
in the same window, not per-employee, so the Message Batches API discount
in `docs/CLAUDE_API_INTEGRATION.md` applies — and notifying managers via
`notification` when anything lands in the review queue.

## Inputs

None yet.

## Outputs

None yet. Will create/transition `ReviewCycle` rows and trigger
`scoring`/`notification` runs.

## Events

Triggers the biweekly scoring pipeline and the weekly staffing workflow,
per CLAUDE.md's per-service README convention. Not implemented yet.
