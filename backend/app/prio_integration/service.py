"""Business logic for the PRIO Task Tracker integration.

Currently just the status-vocabulary guard. Aggregation logic
(`fde_aggregation_plan.md` §1-4: tickets_closed, on_time_rate, reopen_count)
and the `prio_snapshots` writer are future work (Phase 2 Days 7-9) — they
depend on FDE roster resolution in PRIO, which isn't settled yet (connector
doc §6.5).
"""

from __future__ import annotations

from app.prio_integration import repository
from app.prio_integration.client import PrioMcpClient
from app.prio_integration.exceptions import PrioStatusVocabularyMismatchError

EXPECTED_STATUS_VOCABULARY_VERSION = "status-v1"


def assert_status_vocabulary(client: PrioMcpClient | None = None) -> None:
    """Fail closed if PRIO's status vocabulary has moved past what our reopen/closed logic expects.

    Whatever kicks off a sync or scoring pass against PRIO (the future
    scheduler/aggregation job) must call this first and let the exception
    propagate — per CLAUDE.md's insecure-design control, a version bump is a
    signal to hold and re-check the logic, not something to catch and
    silently continue past.
    """
    vocabulary = repository.get_status_vocabulary(client)
    if vocabulary.version != EXPECTED_STATUS_VOCABULARY_VERSION:
        raise PrioStatusVocabularyMismatchError(
            f"Expected status vocabulary '{EXPECTED_STATUS_VOCABULARY_VERSION}', got '{vocabulary.version}'."
        )
