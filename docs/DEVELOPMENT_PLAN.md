# Development Plan

Day-wise build plan for one full-time solo developer, ~56 working days
(~11 weeks). Built from the actual current state of the codebase (see
"Starting point" below), the build order in the root [`README.md`](../README.md),
and the process/security requirements in `.claude/CLAUDE.md`. Re-baseline the
day counts if team size changes — this assumes one person carrying the full
stack sequentially.

## Starting point (as of this plan's creation)

Only the data model and a bare API skeleton exist:

- Tables: `employees`, `review_cycles`, `prio_snapshots`, `performance_scores`,
  `availability` (see `backend/alembic/versions/a2f53062f9a9_initial_schema.py`).
- `backend/app/main.py` exposes a single `/health` endpoint. No routers,
  services, repositories, auth, Prio/Graph/Claude integration, dashboards,
  tests, or CI exist yet.
- Stale compiled modules (`mismatch`, `self_report`, `client`, `project`,
  `employee_project_allocation`) reference models that have no current
  source file — the intended schema for self-reports and mismatch tracking
  needs to be decided before Phase 1 builds on top of it.

## External blockers — start these immediately, don't wait for their phase

- **Prio MCP connector**: live on staging as of 2026-09-30 — see
  `docs/PRIO_MCP_CONNECTOR.md` for connection details, the tool list, and
  changes this makes to the `docs/fde_aggregation_plan.md` §1–4 query
  approach (status vocabulary, reopen detection, history completeness).
  Production isn't enabled yet, so Phase 2 still develops/tests against
  `docs/prio_schema.sql` sample data or the staging snapshot until it is.
- **IdP app registration** (OIDC/SAML) and **Graph API `Mail.Send` scope
  approval**: typically need IT/tenant-admin action with real lead time.
  Kick off both requests on Day 1.
- **Original product README**: referenced by the root `README.md` as the
  source of truth for the scoring model/weights, but is not in this repo.
  Without it, Phases 3–4 are guessing at thresholds — track this down before
  those phases start.

---

## Phase 0 — Reconcile & plan (Day 1)

- Resolve the stale `.pyc` mystery: decide the real target schema for
  mismatch flags, self-report/profile text storage, and cost logs before
  building on top of it.
- Get the original product README.
- Kick off IdP app registration and Graph API `Mail.Send` scope requests.
- Set up project tracking (issues/board) mirroring the phases below.

## Phase 1 — Data model completion + auth foundation (Days 2–5)

- **Day 2**: Design and migrate: `self_reports` (employee_id, cycle_id,
  profile_text, submitted_at), `mismatch_flags` (cycle_id, employee_id,
  dimension, self_report_claim, tracker_fact, resolved, resolved_by),
  `api_call_logs` (schema from `docs/COST_LOGGING_AND_OPTIMIZATION.md`
  §Schema, append-only).
- **Day 3**: Restructure `app/` into per-service modules per CLAUDE.md §2
  (`employee_profile/`, `review_workflow/`, `scoring/`, `prio_integration/`,
  `notification/`, `scheduler/`), each with `router.py`/`service.py`/
  `repository.py`. Move existing models under the owning service.
- **Day 4**: Auth foundation stub — JWT validation dependency (role +
  employee_id claims), a mock/dev IdP for local work, and the row-level
  authorization pattern from `docs/ARCHITECTURE.md`
  (`WHERE employee_id = :caller_id` baked into the query builder, never
  client-supplied). Wire Ruff + Black + mypy strict + pre-commit per
  CLAUDE.md §2.
- **Day 5**: Pydantic request/response schemas for Employee/Profile
  endpoints; typed exception classes (`ValidationError`,
  `UpstreamIntegrationError`, `AuthorizationError`) + FastAPI exception
  handlers mapping to generic client messages. Basic CI skeleton: lint +
  mypy + pytest on PR.

## Phase 2 — Prio tracker ingestion (Days 6–10)

- **Day 6**: `prio_integration` service scaffold; load `docs/prio_schema.sql`
  into a local sandbox DB as the dev-time stand-in for the live connector.
- **Day 7–8**: Implement the aggregation queries from
  `docs/fde_aggregation_plan.md` (§2–4): completion events via `audit_logs`
  (never `tasks.completed_at`), `on_time_rate` with null-exclusion for
  no-due-date tasks, reopen detection via the hard-coded backward-transition
  list, always joining through `task_assignments` (never `owner_id`).
- **Day 9**: Snapshot writer — validate/sanitize every field with Pydantic
  before persisting to `prio_snapshots` (Injection control, CLAUDE.md §4);
  handle deleted-user joins explicitly ("former employee") per §5's known
  gaps.
- **Day 10**: Circuit breaker + backoff on Prio calls (fail closed → hold
  cycle, alert — never score on stale data); contract test against the
  sandboxed schema.

## Phase 3 — Deterministic scoring pass (Days 11–13)

- **Day 11**: Pure-code scoring functions for Execution, Troubleshooting,
  Ownership (lookup-table/threshold style, per
  `docs/COST_LOGGING_AND_OPTIMIZATION.md` — no LLM). Get real thresholds
  signed off by manager stakeholders, not guessed.
- **Day 12**: Wire these into `performance_scores` writes for the 3
  tracker-only dimensions; unit tests covering every threshold boundary.
- **Day 13**: End-to-end test: tracker sync → aggregation → deterministic
  score, with zero API cost — first fully working (partial) pipeline slice.

## Phase 4 — AI scoring agent (Days 14–20)

- **Day 14**: `scoring` service Claude client wrapper; define the
  `record_dimension_assessment` tool schema from
  `docs/CLAUDE_API_INTEGRATION.md`; env-based model config (never
  hard-coded model per call).
- **Day 15–16**: Self-report vs. tracker cross-check call (small/cheap model
  tier) — treat self-report text as untrusted, strip instruction-like
  content before prompt inclusion (prompt-injection control, CLAUDE.md §6).
- **Day 17**: Documentation rubric grading (stronger model tier, real
  artifact sent as document content, not paraphrased).
- **Day 18**: Coaching-tip generation (cheap tier) + Communication dimension
  drafting (always routed to review, never auto-accepted).
- **Day 19**: Structured-output validation (range/non-empty/required-field
  checks) before any write to the Score Store; `api_call_logs` writer wired
  in from day one, not retrofitted.
- **Day 20**: Prompt caching on the static rubric/system-prompt prefix;
  Message Batches API for the biweekly run; benchmark model tiers against a
  small human-graded sample before locking them in.

## Phase 5 — Manager review workflow (Days 21–25)

- **Day 21–22**: `review_workflow` service — exception routing (default-deny
  to manager review on any confidence/mismatch ambiguity, per Insecure
  Design control, CLAUDE.md §4).
- **Day 23**: Approve/edit/override endpoints, `role = manager` enforced
  server-side; weighted overall-% computation on approval.
- **Day 24**: Append-only audit logging for every approval/override/mismatch
  resolution (actor, timestamp, before/after) — the system of record per
  CLAUDE.md §7.
- **Day 25**: Idempotency pass — keyed writes on
  `(employee_id, cycle_id, dimension)` so a retried partial cycle never
  double-writes or double-counts cost.

## Phase 6 — Real IdP integration (Days 26–29)

- **Day 26–27**: Swap dev auth stub for real OIDC/SAML against the
  enterprise IdP; validate signature/issuer/audience on every request;
  short-lived tokens + refresh rotation.
- **Day 28**: MFA enforcement for manager/admin roles; session revocation on
  role change/offboarding.
- **Day 29**: Rate limiting + account lockout on login paths; integration
  tests against a sandboxed IdP tenant (never production).

## Phase 7 — Dashboards (Days 30–39)

- **Day 30–31**: Frontend scaffold, API client, auth flow (token storage,
  refresh).
- **Day 32–34**: Employee dashboard — own-record-only views (scores,
  coaching tips, profile/self-report submission form).
- **Day 35–37**: Manager dashboard — team-scoped views, review queue,
  approve/edit/override UI wired to Phase 5 endpoints.
- **Day 38**: CSP + output encoding on self-report free-text rendering
  (stored/reflected XSS control); CSRF tokens on all state-changing
  requests.
- **Day 39**: Cross-role access-control test cases (an employee hitting
  another employee's data, a manager hitting another manager's team) — must
  fail server-side regardless of client UI state.

## Phase 8 — Scheduling & notifications (Days 40–44)

- **Day 40**: `scheduler` service — biweekly cadence trigger; autoscaling
  limits so the trigger endpoint can't be used to flood compute.
- **Day 41–42**: `notification` service — Graph API integration, OAuth
  least-privilege (`Mail.Send` only), encrypted refresh tokens;
  profile-update reminders + review-queue alerts.
- **Day 43**: Monitor anomalous send volume; retry/backoff, never
  retry-storm Prio or Graph.
- **Day 44**: Full biweekly-cycle end-to-end test: reminder → tracker sync →
  scoring → review → notification.

## Phase 9 — Security hardening pass (Days 45–48)

- **Day 45**: Outbound allow-list (Prio/Graph/Claude/IdP only) at the
  network layer; SSRF review of any URL built from stored config.
- **Day 46**: Secrets migrated to a secrets manager; `.env.example` audited
  for placeholder-only values; TLS/HSTS verification on every hop.
- **Day 47**: Bandit/Semgrep SAST wired into CI; pip-audit/dependency scan;
  container image scan.
- **Day 48**: Fix findings from Days 45–47; two-reviewer requirement
  enforced on auth/scoring/integration PRs going forward.

## Phase 10 — Testing, monitoring, IaC (Days 49–53)

- **Day 49–50**: Fill out the testing pyramid — unit tests on
  scoring/validation, integration tests against sandboxed tenants, contract
  tests per external adapter.
- **Day 51**: Structured JSON logging with correlation IDs across service
  boundaries; alerting on auth failures, override-rate anomalies,
  integration timeouts.
- **Day 52**: Terraform/Pulumi for environment/network config (segmentation:
  presentation / core services / Score Store subnets).
- **Day 53**: Backup/restore drill for the Score Store; document RTO/RPO.

## Phase 11 — Pre-deployment (Days 54–56)

- **Day 54**: Walk the full Pre-Deployment Security Checklist
  (CLAUDE.md §9) item by item.
- **Day 55**: Staging deploy against sandbox Prio/Graph/IdP tenants; smoke
  test full pipeline.
- **Day 56**: Incident-response runbook review, on-call rotation
  confirmation, schedule the annual pen test; tagged production release.
