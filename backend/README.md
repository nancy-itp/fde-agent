# FDE Platform — Backend

FastAPI backend for the FDE Team Performance Tracking System. See
[../docs/DEVELOPMENT_PLAN.md](../docs/DEVELOPMENT_PLAN.md) for the
day-by-day build plan and current status, [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
for the system design, and [../.claude/CLAUDE.md](../.claude/CLAUDE.md) for
the coding/security standards every PR is held to.

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt   # includes requirements.txt + lint/type/test tooling
copy .env.example .env        # then edit DATABASE_URL if needed
pre-commit install            # from the repo root, with this venv active
```

Requires a running PostgreSQL instance matching `DATABASE_URL` in `.env`.

Lint/type/test gates (Ruff, Black, mypy strict, pytest — see
`pyproject.toml`) run via `pre-commit` on every commit. The pre-commit hooks
call `black`/`ruff`/`mypy` directly (not pre-commit's own isolated
per-hook environments), so **this venv must be active** in whatever shell
you run `git commit` from — `pre-commit run --all-files` will fail with
"Executable not found" otherwise.

## Run migrations

```bash
alembic upgrade head
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Then check `GET http://localhost:8000/health`.

## What's implemented

See `docs/DEVELOPMENT_PLAN.md` for the authoritative day-by-day plan and
current status — this section is a quick orientation, not the source of
truth.

- FastAPI app with `/health` (liveness) and `/prio/health` (PRIO MCP
  connector reachability) endpoints, plus `auth` (dev-login JWT issuance)
  and `employee_profile` (own-record-only profile/availability/scores)
  routes.
- Six per-service modules under `app/` (CLAUDE.md §2's one-module-per-Core-
  Application-Service structure): `employee_profile`, `prio_integration`,
  and `auth` have real router/service/repository logic; `scoring`,
  `review_workflow`, `scheduler`, and `notification` are documented
  skeletons (model + empty router/service/repository, each with a
  `README.md` explaining what's not built yet and which phase builds it).
- 8 tables across those services' `models.py` files: `employees`,
  `review_cycles`, `prio_snapshots`, `performance_scores`, `availability`,
  `self_reports`, `mismatch_flags`, `api_call_logs`. Every table except
  `api_call_logs` (an append-only event log, not a user-editable entity)
  carries a standard audit trail (`created_at`, `created_by`, `updated_at`,
  `updated_by` — see `app/core/mixins.py`), enum columns for constrained
  fields, and check constraints for value ranges.
- `employees.is_active` flags active vs. inactive employees;
  `employees.skills_updated_at` is set by the application whenever
  `skills` changes (not the generic audit `updated_at`), feeding a
  "no skill growth in N cycles" query not yet built.
- `availability.client_name`/`project_name`/`allocation_percent` — which
  client project an employee is currently staffed on and at what
  percentage. Plain text fields, not FKs — kept intentionally simple. One
  project per employee at a time, one row per employee.
- A PRIO MCP connector (`app/prio_integration/`) verified live against
  staging — see its own `README.md` for what's implemented vs. deferred.
- Ruff + Black + mypy (strict) wired and passing, via `pyproject.toml` and
  `.pre-commit-config.yaml` (repo root).
- Two Alembic migrations (initial schema, then the three tables above) —
  safe to extend with new `alembic revision` files as requirements evolve.

## Not yet implemented

- The `scoring`/`review_workflow`/`scheduler`/`notification` services'
  actual logic (see each one's `README.md`) — AI scoring agent, manager
  approve/edit/override endpoints, biweekly cadence trigger, Graph API
  email sends.
- Microsoft Graph connector.
- Real OIDC/SAML IdP integration (currently a hard-gated dev-only
  `/auth/dev-login` stub).
- CI (lint/mypy/pytest-on-PR workflow) and a pytest test suite — the
  tooling is wired and passing locally, but nothing runs it automatically
  yet.
- The skill-stagnation / low-score-trend reporting queries described
  above — computed-on-read, no `flags` table, but no endpoint yet either.
