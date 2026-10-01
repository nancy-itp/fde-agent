# PRIO Integration

Adapter service wrapping PRIO's read-only MCP server (see
`docs/PRIO_MCP_CONNECTOR.md` for the full connection/tool reference this
module implements against). No other service in this backend should call
PRIO directly — always go through here, so retry/circuit-breaker/rate-limit
behavior and response validation live in one place.

## Status

Connector layer only (this pass). Implemented: HTTP transport, auth,
per-tool typed wrappers, and the status-vocabulary guard. **Not yet
implemented**: the `fde_aggregation_plan.md` aggregation queries
(tickets_closed / on_time_rate / reopen_count), the `prio_snapshots`
writer, and FDE roster resolution (connector doc §6.5) — these are Phase 2
Days 7-9 per `docs/DEVELOPMENT_PLAN.md` and depend on a decision that hasn't
been made yet.

All 13 usable tools were exercised live against staging on 2026-09-30 once
the token was issued, and every response schema in `schemas.py` was checked
against a real payload (not just the connector doc's prose) — see that
file's docstring for what changed as a result. Two things worth knowing this
uncovered:

- The real transport is standard MCP `tools/call` over JSON-RPC 2.0 — a
  tool's payload comes back JSON-encoded a second time inside
  `result.content[0].text`, not a flat `{data, isError}` envelope. `client.py`
  implements the real shape now; it was wrong (a plausible-looking guess) on
  the first pass.
- `get_assignment_history`, `list_teams`, `list_team_members`, and
  `find_similar_tasks` do **not** use the `{items, total, next_cursor}`
  pagination envelope the connector doc's §2 claims for "list responses" —
  each has its own bespoke shape. See each schema's docstring in
  `schemas.py` for the confirmed real shape.

## Layout

- `client.py` — the only module that opens a network connection. Handles
  the JSON-RPC 2.0 request/response envelope, auth headers, the 120-calls/min
  rate limit, retry with exponential backoff (honoring each error's
  `retryable` flag and `retry_after` where given), and a circuit breaker
  that fails closed once PRIO looks down. Also the one place that decides
  what becomes a raised exception's message — PRIO's raw error text (which
  can be a pydantic validation traceback, not just the documented
  `{code, message, retryable}` JSON) is always logged, never passed through,
  since `app.main`'s handler renders an `AppError`'s message straight to the
  client.
- `schemas.py` — Pydantic models for the MCP error envelope and the
  response shapes verified live against staging (see above). Still
  deliberately partial — `extra="allow"` everywhere as a safety net for
  fields not yet asserted on.
- `repository.py` — one typed function per usable tool (13 of the 18 PRIO
  exposes; the other 5 are the manager/admin approval workflow, which
  returns `FORBIDDEN_SCOPE` for our token and isn't wrapped).
- `service.py` — business logic. Currently just
  `assert_status_vocabulary()`, which any future sync/scoring job must call
  before doing anything else and let raise on mismatch (fail closed, per
  CLAUDE.md's insecure-design control) rather than catching it.
- `exceptions.py` — typed exceptions, all subclassing
  `app.core.exceptions.UpstreamIntegrationError` so `app.main`'s exception
  handler maps every one of them to the same safe, generic client message.

## Inputs

- Config: `PRIO_MCP_BASE_URL`, `PRIO_MCP_TOKEN` (see `app/core/config.py`
  and `.env.example`). Both are optional at the settings level so the rest
  of the app runs without them; `PrioMcpClient` raises
  `PrioMcpConfigurationError` if a call is attempted with either unset.
  Real values belong in the secrets manager for anything beyond local dev —
  see `docs/PRIO_MCP_CONNECTOR.md` §3.
- Per-call arguments: employee/task/team ids, date ranges, pagination
  cursors — see each `repository.py` function's signature.

## Outputs

- Validated Pydantic model instances (or, for tools without a precisely
  documented schema, a `dict[str, JSONValue]`) — never PRIO's raw response
  passed through unchecked, and never PRIO's raw error body surfaced to a
  caller.

## Events

Emits nothing yet (no scheduler/sync job calls this module). Will emit
whatever `prio_snapshots`-writer events Phase 2 defines once that lands.
