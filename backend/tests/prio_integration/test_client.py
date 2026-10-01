"""Unit tests for PrioMcpClient — no network calls.

Live behavior (real JSON-RPC transport, schema validation against actual
staging responses) was verified manually against the real connector; see
`DEV_NOTES.md` (gitignored, not in this repo) for that record. These tests
cover what's safe and useful to assert in CI: the parts of the client that
don't require a live PRIO endpoint.
"""

from __future__ import annotations

import pytest

from app.prio_integration.client import PrioMcpClient, _backoff_seconds, _first_text_block
from app.prio_integration.exceptions import PrioMcpConfigurationError
from app.prio_integration.schemas import JSONValue


def test_call_tool_raises_when_unconfigured() -> None:
    client = PrioMcpClient(base_url=None, token=None)
    with pytest.raises(PrioMcpConfigurationError):
        client.call_tool("get_status_vocabulary", {})


def test_call_tool_raises_when_token_missing() -> None:
    client = PrioMcpClient(base_url="https://example.invalid/mcp", token=None)
    with pytest.raises(PrioMcpConfigurationError):
        client.call_tool("get_status_vocabulary", {})


def test_backoff_is_monotonically_increasing() -> None:
    assert _backoff_seconds(0) < _backoff_seconds(1) < _backoff_seconds(2)


def test_first_text_block_finds_the_text_entry() -> None:
    content: JSONValue = [{"type": "other", "data": "ignored"}, {"type": "text", "text": "hello"}]
    assert _first_text_block(content) == "hello"


def test_first_text_block_returns_none_when_absent() -> None:
    absent: JSONValue = [{"type": "other"}]
    not_a_list: JSONValue = "not-a-list"
    assert _first_text_block(absent) is None
    assert _first_text_block(not_a_list) is None
