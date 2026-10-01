"""Typed exceptions for the PRIO MCP connector.

All subclass `UpstreamIntegrationError` so the FastAPI boundary in
`app.main` maps every one of them to the same safe, generic client message —
none of PRIO's own error bodies or our internal state ever reach a client.
Callers inside the backend (future `prio_integration.service`, the
scheduler/sync job) can still catch these individually to decide whether to
retry, hold a cycle, or route to manager review per CLAUDE.md's
default-deny-on-ambiguity rule.
"""

from __future__ import annotations

from app.core.exceptions import UpstreamIntegrationError


class PrioMcpConfigurationError(UpstreamIntegrationError):
    """Raised when the connector is used before a base URL/token is configured."""

    default_message = "The PRIO integration is not configured."


class PrioMcpUnavailableError(UpstreamIntegrationError):
    """Raised when the circuit breaker is open or a call fails after retries."""

    default_message = "PRIO is temporarily unavailable."


class PrioResultTooLargeError(UpstreamIntegrationError):
    """Raised on `RESULT_TOO_LARGE` — the caller must narrow the query/page size."""

    default_message = "The PRIO query returned too much data; narrow the request."


class PrioNotFoundError(UpstreamIntegrationError):
    """Raised on `NOT_FOUND` — the referenced entity doesn't exist in PRIO."""

    default_message = "The requested PRIO record was not found."


class PrioStatusVocabularyMismatchError(UpstreamIntegrationError):
    """Raised when `get_status_vocabulary` reports a version other than `status-v1`.

    Per `docs/PRIO_MCP_CONNECTOR.md` §6: a version bump is a signal to
    re-check reopen/closed detection logic, not a silent no-op. Whatever
    calls `service.assert_status_vocabulary` should treat this as fail-closed
    (hold the cycle / alert), not proceed with stale assumptions.
    """

    default_message = "PRIO's status vocabulary has changed and needs review before scoring continues."
