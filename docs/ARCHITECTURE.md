# Architecture

## Services

Four independent pieces. Keep them independently deployable — the scoring
agent will change far more often than the dashboards, and you don't want a
prompt tweak to require redeploying the UI.

```
tracker-sync        scheduled job, pulls tracker data into cycle records
scoring-agent        API service, calls Claude, writes drafts + logs
review-api           API service, manager approve/edit/override endpoints
dashboard-api        read-only API service, serves both dashboards
```

`tracker-sync` and `scoring-agent` can be one service if the team is small;
keep them as separate *functions/modules* regardless, so the LLM-calling code
is never accidentally invoked by the sync job or vice versa.

## Why the dashboard can't call the tracker directly

A browser-hosted dashboard cannot call most task trackers' APIs directly —
content-security policy in typical hosting setups blocks it, and even where
it wouldn't, you'd be shipping a tracker credential to every employee's
browser. `tracker-sync` is a backend job that authenticates to the tracker on
a schedule and writes clean, pre-processed snapshots into your own storage.
The dashboards and the scoring agent both read from that snapshot, never from
the tracker directly.

## Request flow, one cycle

```
tracker-sync (scheduled)
   → cycle_record.tracker_snapshot

employee submits profile update
   → cycle_record.profile_text

scoring-agent (triggered once both inputs exist, or on a schedule)
   → deterministic pass: tracker-formula dimensions (no LLM)
   → LLM pass: cross-check, documentation grading, coaching text (see
     CLAUDE_API_INTEGRATION.md)
   → writes ai_draft per dimension + writes to the cost log
   → flags dimensions needing manager review

review-api
   → manager approves / edits / resolves mismatch flags
   → on approval: compute weighted overall %, write final score

dashboard-api
   → manager dashboard: query across all employees
   → employee dashboard: query filtered to caller's own employee id
```

## Auth and role-based access

Two roles: `manager` and `employee`. Enforce the filter server-side in
`dashboard-api` and `review-api` — never rely on the frontend to hide other
employees' data. A practical pattern:

- JWT (or session) carries `role` and `employee_id`.
- Every dashboard-api query for role `employee` has `WHERE employee_id = :caller_id`
  hard-coded into the query builder, not passed as a client-supplied filter.
- `review-api` write endpoints (approve, override, resolve mismatch) require
  `role = manager`, full stop.
- Consider whether a manager should see other managers' teams — the source
  README assumes one manager over the whole 20–23 person team, but if that
  changes, scope the manager role to their own reports.

## Storage

Minimum tables, matching the product README's data model:

- `employees` (id, name, role, resume_data, current_profile)
- `cycle_records` (employee_id, cycle_id, profile_text, tracker_snapshot,
  ai_drafts JSON, manager_scores JSON, overall_pct, approved_at, approved_by)
- `mismatch_flags` (cycle_id, dimension, self_report_claim, tracker_fact,
  resolved boolean)
- `api_call_logs` (see `COST_LOGGING_AND_OPTIMIZATION.md` — this is its own
  table, not folded into cycle_records, so you can query cost independent of
  scoring data and so a logging bug can never corrupt a score)

Keep `api_call_logs` append-only. Never update or delete a row in it — that
log is your audit trail for both cost and for "why did the model draft
this score."

## Scheduling

One cron/scheduled-job trigger for the biweekly cadence: send profile-update
reminders on day 1, run `tracker-sync` continuously (or nightly) throughout
the cycle, run the scoring pass once both a profile update and a fresh
tracker snapshot exist for an employee, and notify the manager when anything
lands in the review queue. Don't run the scoring pass per-employee the moment
their profile update arrives — batching all employees due in the same window
into one run is what makes the Message Batches API discount in
`CLAUDE_API_INTEGRATION.md` worth using.

## Failure handling

- **Claude API errors** (rate limit, timeout, 5xx): retry with backoff at the
  request level; if a cycle's scoring pass fails entirely, leave that
  employee's cycle in a `pending` state and alert — never silently skip a
  cycle or write a partial/zeroed score.
- **Tracker sync failures**: if a snapshot pull fails, don't run scoring for
  that employee on stale or missing tracker data; hold the cycle and alert,
  since four of six dimensions depend on that data being current.
- **Idempotency**: the scoring pass should be safe to re-run for an employee
  whose earlier attempt failed partway — don't double-write drafts or
  double-count API cost in the log if a retry succeeds after a partial
  failure. Key writes on `(employee_id, cycle_id, dimension)`.
