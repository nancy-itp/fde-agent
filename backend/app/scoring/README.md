# Scoring

**Status**: skeleton only (`models.py` is real; `router.py`/`service.py`/
`repository.py` are documented placeholders). Built in
`docs/DEVELOPMENT_PLAN.md` Phases 3-4, Days 11-20.

## Responsibility

Computes per-employee, per-cycle, per-dimension scores: a deterministic
code pass for the three tracker-driven dimensions (Execution,
Troubleshooting, Ownership — never an LLM call for the score itself, per
`docs/COST_LOGGING_AND_OPTIMIZATION.md`), and an AI pass for
self-report/tracker cross-check, documentation rubric grading, and
coaching-tip generation. Owns `PerformanceScore` and `ApiCallLog`
(`models.py`) — the latter is the append-only log every Claude API call
writes to, per dimension/employee/cycle, for cost attribution.

## Inputs

None yet. Will take `prio_integration` aggregates, `SelfReport` free text
(`app.employee_profile.models`), and the documentation artifact per cycle.

## Outputs

None yet. Will write `PerformanceScore` rows (never auto-approved into a
final score — see `review_workflow`) and `ApiCallLog` rows for every model
call.

## Events

Consumes a trigger from `scheduler`; produces drafts that `review_workflow`
reads from its review queue. Not implemented yet.
