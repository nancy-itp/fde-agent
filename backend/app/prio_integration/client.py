"""Streamable HTTP (JSON-RPC 2.0) client for the PRIO MCP connector.

This is the only module in this service that opens a network connection —
`repository.py` calls through here so retry/circuit-breaker/rate-limit
behavior and error handling live in one place. Fails closed: a call that
can't complete safely raises rather than returning partial or stale-looking
data (CLAUDE.md §6, "integration failures fail closed").

PRIO's server is a standard MCP `tools/call` endpoint over JSON-RPC 2.0 (its
own validation errors reference the MCP SDK's `JSONRPCRequest`/
`JSONRPCResponse` types), not the simplified `{tool, arguments}` /
`{isError, data}` envelope the connector doc's prose implies. A tool's
result comes back as `result.content[0].text` — a JSON *string* that must be
parsed a second time — and a tool-level error comes back as
`result.isError: true` with that same text field holding either PRIO's
documented `{code, message, retryable}` JSON (prefixed with
`"Error executing tool <name>: "`) or, for a malformed call, a raw pydantic
validation traceback that isn't JSON at all. Verified live against staging
on 2026-09-30 — see `_send`/`_parse_tool_error_text`.

Every raw PRIO error string is logged, never attached to a raised
exception's message: `app.main`'s exception handler renders whatever
message is on an `AppError` directly to the client, so passing PRIO's text
through would violate CLAUDE.md §4 ("raw stack traces or upstream error
bodies ... must never reach the client").

TLS verification deliberately uses the OS's native trust store
(`ssl.create_default_context()` with no `cafile` override) instead of
`httpx`'s default, which bundles `certifi`'s CA file. Profiled 2026-09-30:
on at least one dev machine, `ssl.SSLContext.load_verify_locations()`
parsing `certifi`'s ~120-certificate bundle took ~20-30s (a constant
~200ms/certificate — the signature of something intercepting OpenSSL's
certificate-loading calls, most likely endpoint security software), while
the OS trust store path took 18ms. This is a real, vetted alternative (not
custom crypto — CLAUDE.md §4 is about not hand-rolling cryptography, and
using the platform's own trust store is a standard `ssl` module code path),
and arguably more correct for a server besides: it also honors any
enterprise root CA already installed on the host.
"""

from __future__ import annotations

import itertools
import json
import logging
import ssl
import time
from dataclasses import dataclass
from threading import Lock

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import UpstreamIntegrationError
from app.prio_integration.exceptions import (
    PrioMcpConfigurationError,
    PrioMcpUnavailableError,
    PrioNotFoundError,
    PrioResultTooLargeError,
)
from app.prio_integration.schemas import JSONValue, McpErrorCode, McpToolError

logger = logging.getLogger(__name__)

_RATE_LIMIT_PER_MINUTE = 120
_RATE_LIMIT_WINDOW_SECONDS = 60.0
_CIRCUIT_FAILURE_THRESHOLD = 5
_CIRCUIT_RESET_SECONDS = 60.0
_MAX_ATTEMPTS = 3
_BASE_BACKOFF_SECONDS = 0.5
_MAX_RETRY_SLEEP_SECONDS = 30.0

_ERROR_EXCEPTIONS: dict[McpErrorCode, type[UpstreamIntegrationError]] = {
    "RESULT_TOO_LARGE": PrioResultTooLargeError,
    "NOT_FOUND": PrioNotFoundError,
    "UNAUTHENTICATED": PrioMcpConfigurationError,
    "FORBIDDEN_SCOPE": PrioMcpConfigurationError,
}

_request_ids = itertools.count(1)
_request_id_lock = Lock()

# Built once at import time — see the module docstring for why this isn't
# httpx's certifi-based default.
_ssl_context = ssl.create_default_context()


def _next_request_id() -> int:
    with _request_id_lock:
        return next(_request_ids)


@dataclass
class _CircuitState:
    failure_count: int = 0
    opened_at: float | None = None


class PrioMcpClient:
    """One tool-call entry point, with rate limiting, retry/backoff, and a circuit breaker."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url if base_url is not None else settings.prio_mcp_base_url
        self._token = token if token is not None else settings.prio_mcp_token
        self._timeout_seconds = timeout_seconds
        self._circuit = _CircuitState()
        self._circuit_lock = Lock()
        self._call_timestamps: list[float] = []
        self._rate_lock = Lock()
        # A persistent client (connection pooling) built once with the OS
        # trust store, rather than a fresh client — and fresh certifi-backed
        # SSL context — on every call.
        self._http_client = httpx.Client(verify=_ssl_context, timeout=timeout_seconds)

    def call_tool(self, name: str, arguments: dict[str, JSONValue]) -> dict[str, JSONValue]:
        """Invoke one named MCP tool and return its parsed result payload.

        Raises a typed `UpstreamIntegrationError` subclass (never PRIO's raw
        error body) on a misconfigured client, an open circuit, a
        non-retryable tool error, or exhausted retries on a retryable one.
        """
        if not self._base_url or not self._token:
            raise PrioMcpConfigurationError()

        self._check_circuit()
        self._throttle()

        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                payload, error = self._send(name, arguments)
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                last_exc = exc
                self._record_failure()
                logger.warning("PRIO MCP transport error calling %s (attempt %d): %s", name, attempt + 1, exc)
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(_backoff_seconds(attempt))
                continue

            if error is None:
                self._record_success()
                return payload

            logger.warning(
                "PRIO MCP tool error calling %s (attempt %d): code=%s retryable=%s",
                name,
                attempt + 1,
                error.code,
                error.retryable,
            )
            if not error.retryable or attempt == _MAX_ATTEMPTS - 1:
                self._record_failure()
                raise _ERROR_EXCEPTIONS.get(error.code, PrioMcpUnavailableError)()

            last_exc = PrioMcpUnavailableError()
            self._record_failure()
            sleep_seconds = error.retry_after if error.retry_after is not None else _backoff_seconds(attempt)
            time.sleep(min(sleep_seconds, _MAX_RETRY_SLEEP_SECONDS))

        raise PrioMcpUnavailableError("PRIO MCP call failed after retries.") from last_exc

    def _send(self, name: str, arguments: dict[str, JSONValue]) -> tuple[dict[str, JSONValue], McpToolError | None]:
        """POST one JSON-RPC 2.0 `tools/call` request and unwrap its result.

        Returns `(payload, None)` on success or `({}, error)` on a
        tool-level error. Raises `PrioMcpUnavailableError` directly — not
        caught by `call_tool`'s transport-error branch, so it skips retries
        — if the response isn't valid JSON-RPC, carries a protocol-level
        error, or a successful result's content isn't the expected single
        JSON text block: any of those mean our request was malformed or
        PRIO's response shape changed, not a transient failure retrying
        would fix.
        """
        assert self._base_url is not None  # call_tool checks this before _send is ever invoked
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        body = {
            "jsonrpc": "2.0",
            "id": _next_request_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        response = self._http_client.post(self._base_url, json=body, headers=headers)
        response.raise_for_status()
        envelope: dict[str, JSONValue] = response.json()

        if "error" in envelope:
            logger.error("PRIO MCP JSON-RPC protocol error calling %s: %r", name, envelope["error"])
            raise PrioMcpUnavailableError()

        result = envelope.get("result")
        if not isinstance(result, dict):
            logger.error("PRIO MCP response for %s had no usable result: %r", name, envelope)
            raise PrioMcpUnavailableError()

        text = _first_text_block(result.get("content"))
        if text is None:
            logger.error("PRIO MCP response for %s had no text content block: %r", name, result)
            raise PrioMcpUnavailableError()

        if result.get("isError"):
            return {}, _parse_tool_error_text(name, text)

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.error("PRIO MCP successful response for %s was not valid JSON: %r", name, text)
            raise PrioMcpUnavailableError() from None

        if not isinstance(payload, dict):
            logger.error("PRIO MCP successful response for %s was not a JSON object: %r", name, payload)
            raise PrioMcpUnavailableError()

        return payload, None

    def close(self) -> None:
        """Release the underlying connection pool.

        Not required for the process-lifetime singleton `get_prio_mcp_client`
        returns — the OS reclaims it on exit — but useful for tests/scripts
        that construct short-lived `PrioMcpClient` instances directly.
        """
        self._http_client.close()

    def _check_circuit(self) -> None:
        with self._circuit_lock:
            if self._circuit.opened_at is None:
                return
            if time.monotonic() - self._circuit.opened_at >= _CIRCUIT_RESET_SECONDS:
                self._circuit = _CircuitState()
                return
        raise PrioMcpUnavailableError()

    def _record_failure(self) -> None:
        with self._circuit_lock:
            self._circuit.failure_count += 1
            if self._circuit.failure_count >= _CIRCUIT_FAILURE_THRESHOLD and self._circuit.opened_at is None:
                self._circuit.opened_at = time.monotonic()

    def _record_success(self) -> None:
        with self._circuit_lock:
            self._circuit = _CircuitState()

    def _throttle(self) -> None:
        """Stay under PRIO's 120 calls/min by sleeping before an over-quota call."""
        with self._rate_lock:
            now = time.monotonic()
            self._call_timestamps = [t for t in self._call_timestamps if now - t < _RATE_LIMIT_WINDOW_SECONDS]
            if len(self._call_timestamps) >= _RATE_LIMIT_PER_MINUTE:
                sleep_for = _RATE_LIMIT_WINDOW_SECONDS - (now - self._call_timestamps[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
            self._call_timestamps.append(time.monotonic())


def _first_text_block(content: JSONValue) -> str | None:
    if not isinstance(content, list):
        return None
    for block in content:
        if isinstance(block, dict):
            text = block.get("text")
            if block.get("type") == "text" and isinstance(text, str):
                return text
    return None


def _parse_tool_error_text(name: str, text: str) -> McpToolError:
    """Extract PRIO's `{code, message, retryable}` from `"Error executing tool X: ..."`.

    Falls back to a generic non-retryable error if the tail after the
    prefix isn't valid JSON matching that schema — this happens for a
    malformed call, where PRIO returns a raw pydantic argument-validation
    traceback instead of the documented error shape. The raw text is
    logged, never surfaced.
    """
    prefix = f"Error executing tool {name}: "
    payload_text = text[len(prefix) :] if text.startswith(prefix) else text
    try:
        parsed = json.loads(payload_text)
        return McpToolError.model_validate(parsed)
    except (json.JSONDecodeError, PydanticValidationError):
        logger.error("PRIO MCP tool error for %s was not the documented error shape: %r", name, text)
        return McpToolError(code="INTERNAL", message="PRIO returned an unrecognized error.", retryable=False)


def _backoff_seconds(attempt: int) -> float:
    return _BASE_BACKOFF_SECONDS * (2.0**attempt)


_default_client: PrioMcpClient | None = None


def get_prio_mcp_client() -> PrioMcpClient:
    """Process-wide client so the circuit breaker and rate limiter are shared."""
    global _default_client
    if _default_client is None:
        _default_client = PrioMcpClient()
    return _default_client
