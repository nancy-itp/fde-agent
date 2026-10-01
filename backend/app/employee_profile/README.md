# Employee/Profile Management

One of the Core Application Services named in `.claude/CLAUDE.md` §2.

## Inputs

- Verified JWT (via `app.core.security.get_current_employee`) — every route
  reads the caller's `employee_id` from the token, never from a query
  param or body field.
- `PATCH /employees/me/availability` body: employee-self-reported fields
  only (`available`, `skill_set`, `availability_status`, `skills`).
  `client_name`/`project_name`/`allocation_percent` are staffing
  assignments set elsewhere and are not accepted here.

## Outputs

- `GET /employees/me` — own profile.
- `GET /employees/me/availability` — own availability record.
- `GET /employees/me/scores?cycle_id=` — own `performance_scores` rows,
  defaulting to the current open cycle.
- `GET /cycles/current` — the current open review cycle (temporary home;
  moves to `review_workflow` once that service exists).

## Events emitted/consumed

None yet — this service is read/self-service only. It will consume
`performance_scores` writes from the future Scoring service and
`review_cycles` writes from the future Scheduler, but emits nothing itself.
