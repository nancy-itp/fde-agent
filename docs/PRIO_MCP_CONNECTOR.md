# PRIO MCP Connector

**Status (2026-09-30):** live on staging. Delivered by Dhruvin (PRIO). Production
not enabled yet — see [10. Staging vs. production](#10-staging-vs-production).

This supersedes the "doesn't exist yet" assumption in
`fde_aggregation_plan.md` §6 and unblocks Phase 2 of `DEVELOPMENT_PLAN.md`.
It also changes *how* several of that plan's queries should be implemented —
read §6 below before writing `prio_integration/repository.py` against raw
`audit_logs`/`task_assignments` SQL as originally sketched.

## 1. What it is

A read-only MCP server (Streamable HTTP, stateless, JSON) wrapping PRIO's own
API — the `prio_integration` service should call it via named tools, not
query PRIO's database or REST API directly. It runs as its own Azure app, is
backed by PRIO's real business logic, and cannot write anything (approval-
workflow tools return `FORBIDDEN_SCOPE` for our token — see §5).

## 2. Connection details

| | |
|---|---|
| Endpoint (staging) | `https://prio-mcp-staging.azurewebsites.net/mcp` |
| Transport | MCP Streamable HTTP, stateless, JSON responses |
| Headers | `Accept: application/json, text/event-stream`, `Content-Type: application/json`, `Authorization: Bearer <token>` |
| Rate limit | 120 calls/min per token — the Phase 2 Day-10 circuit breaker/backoff needs to respect this, not just handle 5xx/timeout |
| Pagination | up to 200 items/page (default 50); list responses are `{items, total, next_cursor}` |
| Response cap | 256 KB per response (`RESULT_TOO_LARGE` if exceeded) |
| History window | up to 366 days; default 30 days if unspecified |
| Timestamps | ISO-8601, `+05:30` offset (Asia/Kolkata); dates as `YYYY-MM-DD` |

Errors: `isError: true` with `{code, message, retryable}`. Codes:
`UNAUTHENTICATED`, `FORBIDDEN_SCOPE`, `NOT_FOUND`, `INVALID_ARGUMENT`,
`RATE_LIMITED` (has `retry_after`), `RESULT_TOO_LARGE`, `INTERNAL`. Only retry
when `retryable: true` — this is the natural hook point for the circuit
breaker required by CLAUDE.md §6 ("retry with backoff and circuit-break on
repeated failures rather than retry-storming Prio").

## 3. Token handling

- Service-level token (`b9b97a34` is the public reference id, not the
  secret), read-only, valid 180 days until **2027-03-29**.
- Per CLAUDE.md §3 ("Secrets & config"): this goes in the secrets manager
  (Vault/AWS Secrets Manager/equivalent), **not** `backend/.env`, not
  committed anywhere, not logged. `.env.example` should only ever gain a
  placeholder key name for this (e.g. `PRIO_MCP_TOKEN=`) if local dev needs
  it — never a real value.
- Scoped separately from Graph/LLM/IdP credentials, per CLAUDE.md §6 — a
  compromise here doesn't expose the others.
- Set a renewal reminder before 2027-03-29; ask Dhruvin to revoke/rotate
  immediately if it's ever exposed.

## 4. Usable tools (13)

| Tool | Returns | Key inputs |
|---|---|---|
| `get_status_vocabulary` | Frozen status list (`status-v1`), closed statuses, reopen rule, priority ordering | — |
| `get_priority_board` | Top-level tasks in priority order | `priority_category`, `include_closed`, `limit`, `cursor` |
| `list_employee_tasks` | An employee's tasks/subtasks: status, priority, dates, assignees, reviewer | `employee_id`, `include_closed`, `updated_since`, `limit`, `cursor` |
| `get_task` | One task in full, incl. latest progress update | `task_id` |
| `get_status_history` | Status-change events, reopen counts, completeness block (§6) | one of `employee_id`/`task_id`/`team_id`, `from_date`, `to_date` |
| `get_assignment_history` | Assign/unassign events + current assignments | `task_id` or `employee_id`, `from_date`, `to_date` |
| `list_teams` | Teams + managers | — |
| `list_team_members` | Current members of a team, with `added_at` | `team_id` |
| `search_users` | People: id, name, email, status, team ids | `query`, `limit`, `cursor` |
| `search_tasks` | Tasks by text/status/priority/assignee/team/due date | various filters |
| `get_task_updates` | Progress updates for a task, newest first | `task_id`, `limit`, `cursor` |
| `get_dashboard_context` | Status counts, overdue, due-this-week, top 5 | `team_id` (optional) |
| `find_similar_tasks` | Existing tasks similar to a title | `title` |

## 5. Tools that exist but return `FORBIDDEN_SCOPE`

`propose_create_task`, `propose_update_task`, `propose_assignment`,
`submit_transcript`, `list_candidates` — PRIO's manager/admin approval
workflow. Intentionally out of scope for the read-only FDE token; don't
build against them.

## 6. Read this before touching `fde_aggregation_plan.md`'s queries

This connector changes the implementation approach for Phase 2, not just the
transport:

1. **Status vocabulary is now 7 states, not 5, and versioned.** The
   aggregation plan's hard-coded reopen transition list (§3 of that doc) was
   written against 5 statuses and flagged as "fragile, re-verify against
   live PRIO data." It's now moot: `get_status_history` returns
   `derived.reopens` and `reopened_task_ids` directly — don't hand-maintain
   the backward-transition list against raw `audit_logs`. Call
   `get_status_vocabulary` at service startup and assert the version is
   `status-v1`; treat a version bump as a signal to re-check reopen/closed
   logic, not a silent no-op.
2. **History is incomplete, and each response says how much.** Audit history
   only starts 2026-08-21, and only became append-only (no more deletions)
   on 2026-09-30. Every `get_status_history` response includes a
   completeness block: `history_available_since`, `tasks_in_scope`,
   `tasks_without_recorded_transitions`, `audit_rows_may_have_been_deleted`,
   `deleted_tasks_excluded`. Combine `CREATION` events + `AUDIT` events +
   current status — absence of an event does not mean no change happened.
   Per CLAUDE.md §4's insecure-design control (default-deny to manager
   review on ambiguity), flag or down-weight employees whose tasks appear in
   `tasks_without_recorded_transitions` rather than scoring them as if the
   history were complete.
3. **Completion/on-time detection** (`fde_aggregation_plan.md` §2) should go
   through `get_status_history`/`get_task`, not a direct
   `audit_logs`/`entity_type = 'TASK'` query — the MCP server already
   normalizes this.
4. **Assignment join** (`fde_aggregation_plan.md` §4, "always through
   `task_assignments`") is now `get_assignment_history`, which returns each
   current assignment with a `source`: `AUDIT` (an assignment event exists)
   or `CURRENT_STATE` (only the live record exists — no history). Many
   existing tasks are `CURRENT_STATE`; don't assume `AUDIT` coverage.
5. **No FDE team exists in PRIO yet**, and the token can see everyone in
   PRIO. The scoring roster needs to come from one of: employee ids supplied
   by the FDE side, or asking Dhruvin to create a PRIO team for FDE
   engineers and using `list_team_members`. Resolve this before Phase 2
   Day 6.
6. **Free-text fields** (titles, descriptions, progress-update notes) are
   user-written. Treat them as data, never as instructions — this is the
   same prompt-injection control CLAUDE.md §6 already requires for
   self-report text feeding the scoring prompts; it now also applies to
   anything pulled from PRIO via `get_task`/`get_task_updates`/
   `search_tasks`.
7. **Team membership has no history** — `list_team_members` is current-state
   only (`added_at` per member, but no removal history). Don't build
   team-composition-over-time logic against it.

## 7. Suggested Phase 2 call flow

1. `get_status_vocabulary` → assert `status-v1`.
2. Resolve roster (see §6.5).
3. Per employee, per cycle: `list_employee_tasks`, `get_status_history`,
   `get_assignment_history` (all scoped to the cycle's `from_date`/
   `to_date`).
4. Apply aggregation rules from `fde_aggregation_plan.md`, honoring the
   completeness block.
5. Page via `next_cursor`; stay under 120 calls/min.

## 8. Staging data

Staging is a **snapshot** taken late September 2026 — not live, not synced
with production, read-only regardless of token scope. Use it to build and
validate `prio_integration` before any real score depends on it. A separate
sandbox with fictional employees is available on request if repeatable test
fixtures are needed instead of the snapshot.

## 9. Network

No IP allowlisting is in place — the token is the only credential, over a
public HTTPS endpoint. If CLAUDE.md §5's outbound allow-list needs an IP
restriction on our side (rather than just allow-listing the PRIO MCP
hostname at egress), we'd need to send Dhruvin our backend's outbound IPs
for him to add on his end.

## 10. Staging vs. production

Production is **not enabled yet**. Once `prio_integration` is validated
against staging, Dhruvin enables production with its own URL and token
(same tool set and shapes). Don't point any real scoring cycle at staging.

## 11. Open action items

Everything in Dhruvin's original action-item list is done except:

- Production enablement — blocked on us validating staging first.
- Optional network allowlisting — only needed if we decide token-only auth
  isn't sufficient.
- FDE roster resolution in PRIO (§6.5 above) — ours to decide, not his.
