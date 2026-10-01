# Cost logging and optimization

Two separate problems, both handled here: (1) log every Claude API call in
enough detail to make cost decisions from the data instead of guessing, and
(2) a decision framework for which parts of the scoring pipeline should
never call an LLM in the first place.

## Part 1: which dimensions shouldn't call an LLM at all

Walk the scoring table from the product README against what actually
produces each score:

| Dimension | Weight | Primary source | LLM needed for the *score*? |
|---|---|---|---|
| Technical fundamentals & application | 23% | Resume + self-report | Light — see below |
| Practical execution / delivery | 23% | Task tracker | **No** |
| Troubleshooting & problem-solving | 17% | Task tracker | **No** |
| Communication & proactive escalation | 15% | Task tracker + manager | No score-generation; drafted only |
| Documentation habits | 11% | AI rubric grade of artifact | **Yes** |
| Ownership & reliability | 11% | Task tracker | **No** |

That's 51% of total weight (Execution + Troubleshooting + Ownership) coming
from tracker metrics that are already numeric: on-time %, reopen count,
tickets closed, comment activity. Turning those into a 1–5 score is a
lookup-table or weighted-formula problem, not a language problem. Write it
as plain code:

```python
def score_execution(tracker: TrackerSnapshot) -> int:
    if tracker.on_time_pct >= 0.95 and tracker.reopen_rate <= 0.05:
        return 5
    if tracker.on_time_pct >= 0.85 and tracker.reopen_rate <= 0.10:
        return 4
    if tracker.on_time_pct >= 0.70:
        return 3
    if tracker.on_time_pct >= 0.50:
        return 2
    return 1
```

Tune the actual thresholds with your manager team, but the point stands:
this is deterministic, testable, free to run, and instant. **Never send a
tracker snapshot to the model and ask it to compute a numeric score from it**
— that's the single most common way an LLM-first build burns budget on work
a spreadsheet formula already does correctly.

What the LLM *is* genuinely good for, on top of a tracker-driven dimension,
is the human-readable evidence line and coaching tip that accompanies the
code-computed score — that's still worth generating, cheaply, per
`CLAUDE_API_INTEGRATION.md`'s model-tiering guidance. So the pattern per
tracker-driven dimension is: **code computes the score, a small/cheap model
call turns it into one sentence of evidence and one coaching tip** — not
"the model does the whole dimension."

Technical fundamentals draws on the resume (static, read once at onboarding)
and the self-report (free text) — matching free text against a skill
baseline is a genuine language task, so this one keeps an LLM call, but only
for the interpretation step, not for anything that could be pattern-matched
(e.g. don't call the model to check whether a profile update was submitted
at all — that's a null check).

Documentation grading against a rubric, applied to the actual linked
artifact, is inherently a language-understanding task — that one stays an
LLM call, no shortcut. The self-report vs. tracker mismatch detection is
also inherently semantic (comparing a claim in prose against structured
facts) — code can flag obviously-absent evidence, but real
paraphrase-vs-fact comparison needs the model.

**Rule of thumb** when you're deciding whether a new sub-task needs a model
call: if the input is already structured/numeric and the output is a
score, threshold, or boolean, write code. If the input is free text and the
task is genuinely about meaning (matching, comparing, grading against
criteria, summarizing), that's a real LLM task — but keep the call as small
and cheap-tiered as the task allows (see model selection in
`CLAUDE_API_INTEGRATION.md`).

## Part 2: log every LLM call

Log to an append-only `api_call_logs` table (or equivalent event stream),
one row per Claude API call, not one row per cycle. You want granularity at
the call level so you can attribute cost to a specific dimension, a specific
employee, and a specific model tier.

### Schema

| Field | Type | Purpose |
|---|---|---|
| `call_id` | uuid | Primary key |
| `timestamp` | datetime | When the call was made |
| `cycle_id` | string | Which biweekly cycle |
| `employee_id` | string | Which employee this call was scoring |
| `dimension` | string | Which scoring dimension, or `null` for non-dimension calls |
| `call_type` | enum | `cross_check` / `doc_grading` / `coaching_text` / `technical_fundamentals` / `manual_rerun` |
| `model` | string | Exact model string used |
| `batched` | boolean | Sent via Message Batches API or synchronous |
| `input_tokens` | int | From the API response usage block |
| `output_tokens` | int | From the API response usage block |
| `cache_read_tokens` | int | From the API response usage block |
| `cache_creation_tokens` | int | From the API response usage block |
| `estimated_cost_usd` | decimal | Computed from token counts × current rate card, not hard-coded per call |
| `latency_ms` | int | Wall-clock time for the call |
| `status` | enum | `success` / `retried` / `failed` / `validation_failed` |
| `retry_count` | int | How many attempts this call took |
| `routed_to_review` | boolean | Did this dimension's output end up needing manager review |
| `manager_overrode` | boolean, nullable | Filled in later, on manager decision — did they change the AI's score |

Compute `estimated_cost_usd` from a rate-card lookup keyed on model and
date, not a literal number baked into the log-writing code — rates change,
and you want historical rows to reflect what you were actually charged at
the time, which means storing the rate-card version or the raw token counts
as the source of truth and treating the dollar figure as a derived,
recomputable column.

### Sample record

```json
{
  "call_id": "5e2b...",
  "timestamp": "2026-09-29T08:14:03Z",
  "cycle_id": "2026-C19",
  "employee_id": "emp_0231",
  "dimension": "documentation_habits",
  "call_type": "doc_grading",
  "model": "claude-sonnet-4-6",
  "batched": true,
  "input_tokens": 8420,
  "output_tokens": 310,
  "cache_read_tokens": 6200,
  "cache_creation_tokens": 0,
  "estimated_cost_usd": 0.0187,
  "latency_ms": 2140,
  "status": "success",
  "retry_count": 0,
  "routed_to_review": false,
  "manager_overrode": null
}
```

## Part 3: what the logs let you decide

Once this is flowing, run these as recurring queries (weekly is plenty for
a 20–23 person team) rather than reacting call-by-call:

- **Cost per dimension per cycle.** If `doc_grading` is costing far more
  than `coaching_text` generation across the board, that's expected — but
  if `coaching_text` alone is a large share of spend, it's a sign you're
  using too large a model tier for a task that doesn't need it.
- **Cache hit rate.** `cache_read_tokens / (cache_read_tokens + cache_creation_tokens)`
  per batch run. A low hit rate on the batched biweekly run means the
  static prefix isn't actually being reused within the cache window —
  check that the whole team's batch is actually submitted close together in
  time, per `CLAUDE_API_INTEGRATION.md`.
- **Override rate by dimension.** If `manager_overrode` is near-zero for a
  dimension over several cycles, that's a signal the AI draft is reliable
  enough that dimension's review threshold could loosen — or, for a
  tracker-backed dimension, a signal to double-check whether the LLM step
  on top of the code-computed score (the evidence/coaching text) is adding
  anything a template sentence wouldn't.
- **Failed/retried call rate.** A rising `status = failed` rate is an
  infrastructure or prompt-format problem, not a cost problem directly, but
  every retry is a second charged call — treat a spike here as a
  cost-relevant incident too.
- **Cost per employee per cycle**, summed across all `call_type`s. This is
  the number to put in front of whoever owns the budget: total scoring cost
  ÷ headcount ÷ cycles per year gives an annual per-employee figure that's
  easy to reason about and compare against the manager-hours the exception-
  based review model is saving.

## Part 4: alerting

Set a threshold alert (Slack, email, whatever the notification channel from
the product README ends up being) on two things specifically:

- A single cycle's total estimated cost exceeding some multiple (e.g. 1.5×)
  of the trailing average — catches a prompt regression that's bloating
  token counts or a retry loop before it runs for a full cycle unnoticed.
- Cache hit rate on a batch run dropping below a set floor — catches the
  batch window silently breaking (e.g. someone changed the scheduler to
  trickle calls in one at a time instead of submitting together).

Both are cheap to compute from the log table above and catch the two
failure modes — a single bad call spiraling, and a systemic caching
regression — that cost the most if left unnoticed for a full cycle.
