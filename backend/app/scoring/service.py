"""Business logic for the Scoring service.

Not yet implemented. Per `docs/DEVELOPMENT_PLAN.md`:

- Phase 3 (Days 11-13): deterministic, code-only scoring for the
  tracker-driven dimensions (Execution, Troubleshooting, Ownership) — see
  `docs/COST_LOGGING_AND_OPTIMIZATION.md` Part 1 for why these must never
  call an LLM to compute the score itself.
- Phase 4 (Days 14-20): the AI scoring agent — self-report/tracker
  cross-check, documentation rubric grading, coaching-tip generation,
  Communication-dimension drafting (always routed to review, never
  auto-accepted). Every call logged to `ApiCallLog` (`models.py`) from day
  one; structured-output validation before any `PerformanceScore` write;
  treat self-report free text as untrusted input (prompt-injection
  control, CLAUDE.md §6).
"""

from __future__ import annotations
