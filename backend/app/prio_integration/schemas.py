"""Response shapes for the PRIO MCP connector.

Verified 2026-09-30 against real staging responses. `docs/PRIO_MCP_CONNECTOR.md`
describes each tool's purpose and key inputs in prose, not a field-by-field
JSON schema, so every shape below was checked against an actual live
`tools/call` result rather than inferred from the doc alone — several
guesses made before the token was available turned out wrong (e.g.
`get_assignment_history` is not the generic pagination envelope, and
`tasks_without_recorded_transitions` is a count, not a list of ids). Two
tools were not exercised live and are marked below; `extra="allow"` stays on
every model regardless, as a safety net for anything staging returns that
isn't asserted here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]

McpErrorCode = Literal[
    "UNAUTHENTICATED",
    "FORBIDDEN_SCOPE",
    "NOT_FOUND",
    "INVALID_ARGUMENT",
    "RATE_LIMITED",
    "RESULT_TOO_LARGE",
    "INTERNAL",
]


class McpToolError(BaseModel):
    """A parsed `{code, message, retryable}` tool-error object.

    PRIO doesn't return this as clean JSON on the wire — it's embedded in a
    `"Error executing tool X: {...}"`-prefixed text block (see
    `client._parse_tool_error_text`), with a plain-text fallback (e.g. a raw
    pydantic argument-validation traceback) when the tail isn't valid JSON
    at all.
    """

    model_config = ConfigDict(extra="allow")

    code: McpErrorCode
    message: str
    retryable: bool
    retry_after: float | None = None


class PageEnvelope(BaseModel):
    """The `{items, total, next_cursor}` shape.

    Confirmed live for `get_priority_board`, `list_employee_tasks`,
    `search_users`, `search_tasks`, and `get_task_updates`. `list_teams`,
    `list_team_members`, `get_assignment_history` and `find_similar_tasks`
    all list no `limit`/`cursor` in the connector doc's Key Inputs column and
    turned out to use bespoke shapes instead of this one — that correlation
    (has pagination params → uses this envelope) held for every tool tested,
    but isn't a spec guarantee for any future tool.
    """

    model_config = ConfigDict(extra="allow")

    items: list[JSONValue]
    total: int
    next_cursor: str | None = None


class StatusVocabulary(BaseModel):
    """`get_status_vocabulary` result — confirmed shape.

    Real fields beyond `version`: `statuses` (list of
    `{status, meaning, closed}`), `closed_statuses` (list of strings),
    `reopen_rule` (string), `priority_categories` (list of strings, sort
    order), `priority_rule` (string) — none of these are load-bearing yet
    (only `service.assert_status_vocabulary` reads `version`), so they're
    left to `model_extra` rather than asserted field-by-field.
    """

    model_config = ConfigDict(extra="allow")

    version: str


class StatusHistoryCompleteness(BaseModel):
    """The completeness block of `get_status_history` — confirmed shape.

    `tasks_without_recorded_transitions` is a **count** — the connector
    doc's prose reads as if it might be the id list, but the actual ids are
    the separate `tasks_without_recorded_transitions_ids` field. Per the
    live `guidance` field (and the doc's §6.2): absence of an event does not
    mean no change happened — flag/down-weight employees whose tasks show
    up here rather than scoring as if history were complete.
    """

    model_config = ConfigDict(extra="allow")

    history_available_since: str
    tasks_in_scope: int
    tasks_without_recorded_transitions: int
    tasks_without_recorded_transitions_ids: list[JSONValue] = []
    audit_rows_may_have_been_deleted: bool
    deleted_tasks_excluded: bool


class StatusHistoryDerived(BaseModel):
    """The `derived` block of `get_status_history` — confirmed shape."""

    model_config = ConfigDict(extra="allow")

    reopens: int
    reopened_task_ids: list[JSONValue]


class StatusHistoryResponse(BaseModel):
    """`get_status_history` result — confirmed shape.

    Each `events` entry has `source` (`"CREATION"` or an audit-derived
    value) plus `task_id`/`from_status`/`to_status`/`changed_at`/
    `changed_by` — reopen detection should read `derived`, not hand-roll a
    backward-transition list against these (the now-superseded
    `fde_aggregation_plan.md` §3 approach). Events are left as `JSONValue`
    since only `derived`/`completeness` are asserted on so far.
    """

    model_config = ConfigDict(extra="allow")

    events: list[JSONValue] = []
    derived: StatusHistoryDerived
    completeness: StatusHistoryCompleteness


class AssignmentRecord(BaseModel):
    """One entry of `get_assignment_history`'s `current_assignments` — confirmed shape.

    `source` distinguishes an assignment backed by an audit event
    (`"AUDIT"`) from one that only exists as a live record
    (`"CURRENT_STATE"`) — many current tasks are `CURRENT_STATE`; don't
    assume `AUDIT` coverage.
    """

    model_config = ConfigDict(extra="allow")

    source: Literal["AUDIT", "CURRENT_STATE"]


class AssignmentHistoryResponse(BaseModel):
    """`get_assignment_history` result — confirmed shape.

    **Not** the generic pagination envelope — the connector doc's blanket
    "list responses are {items, total, next_cursor}" claim doesn't hold
    here (no `items`/`total`/`next_cursor` at all). Returns `events`
    (assign/unassign audit events, left unmodeled) alongside
    `current_assignments` (validated as `AssignmentRecord`).
    """

    model_config = ConfigDict(extra="allow")

    events: list[JSONValue] = []
    current_assignments: list[AssignmentRecord]


class TeamMember(BaseModel):
    """One entry of `list_team_members`'s `members` — confirmed shape.

    Current-state only — no removal history, per the connector doc §6.7;
    don't build team-composition-over-time logic against this.
    """

    model_config = ConfigDict(extra="allow")

    employee_id: int
    name: str
    added_at: str


class TeamMembersResponse(BaseModel):
    """`list_team_members` result — confirmed shape (bespoke, not paginated)."""

    model_config = ConfigDict(extra="allow")

    team_id: int
    members: list[TeamMember]


class TeamsResponse(BaseModel):
    """`list_teams` result — confirmed shape (bespoke `teams` key, not paginated)."""

    model_config = ConfigDict(extra="allow")

    teams: list[JSONValue]


class SimilarTasksResponse(BaseModel):
    """`find_similar_tasks` result — confirmed shape (bespoke `matches` key, not paginated)."""

    model_config = ConfigDict(extra="allow")

    matches: list[JSONValue]


class DashboardContext(BaseModel):
    """`get_dashboard_context` result — confirmed shape."""

    model_config = ConfigDict(extra="allow")

    as_of: str
    tasks: int
    by_status: dict[str, JSONValue]
    overdue: int
    due_this_week: int
    top_five: list[JSONValue]
