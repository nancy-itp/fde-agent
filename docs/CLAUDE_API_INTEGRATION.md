# Claude API integration

This maps each stage of the scoring pipeline to a specific Claude API
capability, and says which stages need no LLM call at all. Verify exact
model names, prices, and current limits against the live docs before you
build — this doc gives you the shape, not numbers to hard-code:

- API reference: https://docs.claude.com/en/api/overview
- Pricing: https://docs.claude.com/en/about-claude/pricing (or the pricing
  page linked from the Console)
- Prompt caching: https://docs.claude.com/en/build-with-claude/prompt-caching
- Message Batches: https://docs.claude.com/en/api/creating-message-batches

## Pipeline stages, mapped

| Stage | Needs an LLM? | API feature |
|---|---|---|
| Practical execution, Troubleshooting, Ownership scores | No | Plain code — see `COST_LOGGING_AND_OPTIMIZATION.md` |
| Self-report vs. tracker cross-check | Yes | Messages API, tool use for structured output |
| Documentation rubric grading | Yes | Messages API, document/PDF or long-context input |
| Coaching-tip text generation | Yes | Messages API, plain text generation |
| Communication dimension | Partially — AI drafts, manager decides | Messages API, always routed to review |
| All of the above, run for 20–23 employees on a schedule | — | Message Batches API |

Only three of the six dimensions ever touch the model, and one of those
(Communication) is drafted by the model but never auto-accepted regardless
of what it says. Keep that mapping visible in code — it's the difference
between an LLM call that's earning its cost and one that isn't.

## Use tool use for anything the pipeline reads programmatically

Every model output that another part of the system parses (the cross-check
result, the 1–5 score, the evidence line) should come back as a tool call
with a defined input schema, not as free text you regex out of a paragraph.
Define one tool per structured output, e.g.:

```json
{
  "name": "record_dimension_assessment",
  "description": "Record the drafted score and evidence for one scoring dimension.",
  "input_schema": {
    "type": "object",
    "properties": {
      "score": {"type": "integer", "minimum": 1, "maximum": 5},
      "evidence": {"type": "string"},
      "coaching_tip": {"type": "string"},
      "mismatch_detected": {"type": "boolean"},
      "mismatch_detail": {"type": "string"}
    },
    "required": ["score", "evidence", "coaching_tip", "mismatch_detected"]
  }
}
```

This does two things for cost control specifically: it makes output length
predictable (bounding `max_tokens` sanely), and it makes a malformed or
missing field an obvious, loggable failure instead of a silent parsing bug
that you'd only catch by re-reading transcripts.

## Model selection per task

Don't default every call to your biggest model. Match model tier to task
difficulty, and confirm current model names/capabilities against
https://docs.claude.com/en/docs/about-claude/models before wiring this up:

- **Mismatch detection (self-report vs. tracker facts)** is closer to
  structured comparison than open-ended reasoning — a smaller/faster model
  tier is usually sufficient. Only escalate to a larger model if you
  benchmark meaningfully worse accuracy on it.
- **Documentation rubric grading** needs to read an actual artifact (a doc,
  README, runbook) and apply fixed criteria — this benefits from a stronger
  model, since misgrading here has real coaching consequences.
  Send the artifact itself (as document/file content) rather than a
  paraphrase of it, per the product README's requirement to grade the real
  artifact.
- **Coaching-tip generation** is short, low-stakes text generation — a
  smaller/faster model tier is almost always sufficient here too.

Run a small benchmark (a fixed set of real or synthetic cycles, graded by a
human) before locking in tiers per task — don't guess from general
reputation.

## Prompt caching for the rubric and system prompt

The documentation rubric, the scoring dimension definitions, and your system
instructions are identical across all 20–23 employees in a given cycle and
change rarely. Mark that shared prefix as cacheable (`cache_control` on the
static portion of the system prompt) so that a full cycle's worth of calls
pay the cache-read rate instead of the full input rate on every repeated
call. This only pays off if calls for the same cached prefix happen close
together in time — running the whole team's scoring pass in one batched
window (see below) is what makes caching worthwhile here, rather than
letting each employee's pass trickle in whenever their profile update
happens to land.

## Batch the biweekly run

Since scoring genuinely happens on a schedule for the whole team at once,
not on-demand per user action, this is close to the canonical use case for
the **Message Batches API**: submit all pending cross-check, documentation,
and coaching-tip calls for the cycle as one batch, at a meaningful discount
over synchronous calls, and pick up results asynchronously once the batch
completes. Reserve synchronous Messages API calls for anything a manager
triggers interactively (re-running one employee's assessment after they
dispute it, for example) — that's the one path where a human is waiting on
the response.

## Tracker access via connector vs. custom backend

If your task tracker has an official MCP connector compatible with your
agent runtime, prefer it over hand-rolling API calls — it saves you the
auth and pagination code and stays maintained upstream. If it doesn't,
`tracker-sync` (see `ARCHITECTURE.md`) is a small backend service using the
tracker's own REST/GraphQL API with a read-only token — this is unrelated
to the Claude API and shouldn't route through the model at all; it's plain
data ingestion.

## Structured-output validation is still your job

Tool use narrows the failure surface but doesn't eliminate it — always
validate the returned score is in range, the evidence string is non-empty,
and required fields are present before writing a draft to storage. Log a
validation failure the same way you log any other failed call (see
`COST_LOGGING_AND_OPTIMIZATION.md`) rather than silently retrying forever.
