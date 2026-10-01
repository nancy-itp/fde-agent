# FDE Team Performance Tracking System

Production build guide. This repo turns the AI-assisted scoring workflow into a
real system: a scoring agent backed by the Claude API, exception-based manager
review, and a cost/usage logging layer so every LLM call is justified.

This README is the entry point. It assumes you've already read the product
overview (what the system does, the scoring model, the workflow) — that lives
in the original product README. This file, and the three under `docs/`, cover
*how to build it*.

## Doc index

| Doc | Answers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How the pieces fit together, what's a scheduled job vs. a request, auth, storage, deployment shape |
| [`docs/CLAUDE_API_INTEGRATION.md`](docs/CLAUDE_API_INTEGRATION.md) | Exactly where the Claude API sits in the pipeline, which model/mode per task, tool use, prompt caching, batching |
| [`docs/COST_LOGGING_AND_OPTIMIZATION.md`](docs/COST_LOGGING_AND_OPTIMIZATION.md) | The log schema for every LLM call, and the decision framework for "does this need an LLM at all" |

## Build order

Building this in the order below means every stage produces something you can
test before the next stage depends on it.

1. **Data model + storage first.** Stand up the employee/cycle/mismatch-flag
   tables (see the product README's Data Model section) before writing any
   agent code. The agent is worthless without somewhere durable to write
   drafts.
2. **Tracker ingestion.** Get real (or realistic seed) tracker data flowing
   into a cycle record before touching the AI layer. Four of six scoring
   dimensions are tracker-driven — you want that data trustworthy first.
3. **Deterministic scoring pass.** Per `docs/COST_LOGGING_AND_OPTIMIZATION.md`,
   compute the tracker-formula dimensions in plain code, no LLM. This gives
   you a working (partial) score pipeline with zero API cost, and a baseline
   to compare the AI-assisted dimensions against later.
4. **AI scoring agent.** Add the Claude API calls for the dimensions that
   genuinely need judgment: self-report/tracker cross-checking, documentation
   rubric grading, and coaching-tip generation. Wire in logging from day one
   (`docs/COST_LOGGING_AND_OPTIMIZATION.md`) — retrofitting logging after
   the fact means losing your early cost baseline.
5. **Manager review queue.** Exception routing (mismatch, weak evidence,
   Communication dimension) plus the approve/edit UI.
6. **Dashboards.** Manager and employee views, read-only against the score
   store, role-gated.
7. **Scheduling + notifications.** Biweekly cadence job, reminders, review
   alerts — last, because it depends on everything above already working.

## Environments

Use three environments minimum, since this system holds real performance
data and calls a metered API:

- **dev** — synthetic employees, synthetic tracker data, a low-cost model
  for every call regardless of task, no real notifications sent.
- **staging** — real tracker connection (read-only), a small pilot group of
  real or shadow employees, production model selection, notifications routed
  to a test channel only.
- **production** — full team, real notifications, cost alerts wired to a
  real on-call channel.

Never point dev or staging at the production score store — a scoring bug
that writes garbage into real employee history is a much worse incident than
an API cost overrun.

## Secrets

The task tracker's read-only API token and the Claude API key are the two
credentials this system touches. Both are server-side only: the browser
dashboards never see either directly (see `docs/ARCHITECTURE.md` for why the
tracker can't be called from the browser at all). Store both in your
platform's secret manager, not in environment files committed to the repo.
