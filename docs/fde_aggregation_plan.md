# FDE Scoring — PRIO Task-Tracker Aggregation Plan

**For:** Claude Code, building the "task tracker data" input to the FDE
scoring agent.
**Companion file:** `prio_schema.sql` (reverse-engineered PRIO schema — use
it instead of the raw xlsx export, which is too large for context and
contains large embedded transcript/JSON blobs that aren't needed here).
**Context:** FDE Team Performance Tracking System, per the project README.
The scoring agent scores each of 20–23 employees every 2-week cycle across
weighted dimensions; three of those dimensions are sourced primarily from
the task tracker (PRIO). This plan defines exactly what to pull, how to
aggregate it per employee per cycle, and how to handle the gaps that are
known and accepted (not bugs to work around defensively — just real
constraints of the current data).

---

## 1. What to compute, per employee, per 2-week cycle

| Metric | Feeds dimension | Definition |
|---|---|---|
| `tickets_closed` | Practical execution / delivery (23%) | Count of tasks where `status = 'COMPLETED'`, assigned to this employee, where the completion event (see §2) falls inside the cycle window |
| `on_time_rate` | Practical execution / delivery (23%) | Of the tasks above **that have a `due_date`**, the fraction completed on or before it. Tasks with no `due_date` are excluded from the denominator entirely — never counted as late |
| `reopen_count` | Troubleshooting & problem-solving (17%), Ownership & reliability (11%) | Count of backward status transitions (see §3) on tasks assigned to this employee, within the cycle window |
| `update_activity` | Communication & proactive escalation (15%) | **Not yet buildable** — `task_updates` is future scope in PRIO (2 rows exist in the whole system today). Leave this signal empty/null for now; the Communication dimension continues to route to manager judgment per the README's existing design, so this isn't blocking |

Cycle window = the 2-week period the scoring agent is currently drafting
for a given employee (start/end dates supplied by the FDE backend, not
computed here).

## 2. Determining "when a task was completed"

`tasks.completed_at` is **never populated** — do not use it, and do not
treat its emptiness as something to fix. The manager works directly off
status-change history, so that's the actual source of truth:

```sql
-- Completion events in a cycle window, per employee
SELECT
    ta.employee_id,
    al.entity_id AS task_id,
    al.created_at AS completed_at,
    t.due_date
FROM audit_logs al
JOIN tasks t
    ON t.id = al.entity_id
JOIN task_assignments ta
    ON ta.task_id = t.id
WHERE UPPER(al.entity_type) = 'TASK'       -- casing is inconsistent in the source data; normalize it
  AND al.action = 'STATUS_CHANGED'
  AND al.new_value = 'COMPLETED'
  AND al.created_at BETWEEN :cycle_start AND :cycle_end;
```

`on_time_rate` for a given employee/cycle:

```sql
SELECT
    COUNT(*) FILTER (WHERE due_date IS NOT NULL) AS due_task_count,
    COUNT(*) FILTER (WHERE due_date IS NOT NULL AND completed_at::date <= due_date) AS on_time_count
FROM ( -- the completion-events query above )
```

If `due_task_count = 0`, report `on_time_rate` as `null` (no evidence),
not `0%` or `100%` — an employee with no dated tasks that cycle shouldn't
be scored as if they missed every deadline, or as if they hit a perfect
record they never had a chance to miss.

## 3. Determining reopen/rework

There's no dedicated field. A "reopen" is any `STATUS_CHANGED` event that
moves a task **backward**, e.g. `COMPLETED → IN_PROGRESS`,
`IN_PROGRESS → NOT_STARTED`, or into `BLOCKED` from anything further along.
Confirmed with the PRIO developer that this is the intended detection
method — it isn't a workaround.

```sql
SELECT ta.employee_id, al.entity_id AS task_id, al.old_value, al.new_value, al.created_at
FROM audit_logs al
JOIN task_assignments ta ON ta.task_id = al.entity_id
WHERE UPPER(al.entity_type) = 'TASK'
  AND al.action = 'STATUS_CHANGED'
  AND al.created_at BETWEEN :cycle_start AND :cycle_end
  AND (al.old_value, al.new_value) IN (
        ('COMPLETED', 'IN_PROGRESS'),
        ('COMPLETED', 'NOT_STARTED'),
        ('COMPLETED', 'BLOCKED'),
        ('IN_PROGRESS', 'NOT_STARTED'),
        ('IN_PROGRESS', 'BLOCKED')
        -- extend this list if PRIO's status vocabulary changes — see the
        -- "frozen vocabulary" note below
      );
```

**This is a hard-coded status vocabulary** (`NOT_STARTED`, `IN_PROGRESS`,
`COMPLETED`, `BLOCKED`, `NEEDS_MANAGER_REVIEW`). If PRIO ever renames or
adds to these values without telling the FDE side, this query stops
detecting reopens silently — no error, just wrong (too-low) counts. This
was flagged to Dhruvin (PRIO's developer) as something to document and
version on his end; until confirmed, treat this list as fragile and
re-verify it against live PRIO data before trusting the output.

## 4. Assignment join — always through `task_assignments`

`tasks.owner_id` is **always null** in the current data — don't use it.
A task's real assignee(s) live in `task_assignments` (a task can have more
than one row there, i.e. more than one assignee). All queries above join
through it. An employee with `manager_delegated = true` in `users` has
delegated their approvals to their manager — that's a separate concept
from task assignment and shouldn't be conflated with it.

## 5. Known gaps — don't build around these defensively

These are accepted current-state facts, not problems to solve in this
pass:

- `due_date` is optional by design on every task — handled via the
  null-exclusion in §2, not a data quality issue.
- `team_id` is null on a large share of tasks — team-scoped rollups
  (manager dashboard) will undercount until PRIO's team tagging matures.
  Not a blocker for per-employee scoring, which doesn't need team_id.
- `task_updates`, `workstream_id`, `task_type`, `eta_date`, `source_id`,
  `completed_at`, `owner_id` are either future scope or structurally
  unused right now (see comments in `prio_schema.sql`). Don't write
  aggregation logic against them yet.
- Deleted users (hard-deleted from `users`, e.g. ids 1 and 14 in the
  original export) can still appear as `employee_id` in
  `task_assignments`/`team_members`/historical `audit_logs` rows. Handle
  a missing join to `users` explicitly (e.g. label as "former employee")
  rather than dropping the row silently or erroring.

## 6. Where this data comes from at runtime

This plan assumes a live read path into PRIO's actual database/API, not
this xlsx export. Per the integration decision already made: PRIO exposes
this data through a purpose-built MCP server (a thin wrapper over PRIO's
own API, running on Azure alongside PRIO, with its own service-account
auth) rather than the scoring agent connecting to PRIO's production
database directly.

**Update (2026-09-30): the connector is live on staging.** See
`PRIO_MCP_CONNECTOR.md` for connection details, the full tool list, and —
important — how several of the queries above should actually be
implemented: the reopen-detection logic in §3 and the status vocabulary
assumed here (5 states) are both superseded by that doc's §6, which also
covers the history-completeness gaps that affect §1's metrics. Until
`prio_integration` is built against the live connector, this logic can
still be developed and tested against a local copy of `prio_schema.sql`
loaded with sample/exported data.
