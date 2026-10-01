"""Typed wrappers for the 13 read-only PRIO MCP tools.

One function per tool from `docs/PRIO_MCP_CONNECTOR.md` §4. This is the only
module that constructs a tool-call argument dict or reaches into a raw
response — everything above this layer (future `service.py` aggregation
logic) works with the validated schema types from `schemas.py`, never with
`client.call_tool` directly.

The 5 approval-workflow tools from §5 (`propose_create_task`,
`propose_update_task`, `propose_assignment`, `submit_transcript`,
`list_candidates`) are intentionally not wrapped here — they return
`FORBIDDEN_SCOPE` for our read-only token and are out of scope.
"""

from __future__ import annotations

from app.prio_integration.client import PrioMcpClient, get_prio_mcp_client
from app.prio_integration.exceptions import PrioNotFoundError
from app.prio_integration.schemas import (
    AssignmentHistoryResponse,
    DashboardContext,
    JSONValue,
    PageEnvelope,
    SimilarTasksResponse,
    StatusHistoryResponse,
    StatusVocabulary,
    TeamMembersResponse,
    TeamsResponse,
)


def _args(**kwargs: JSONValue) -> dict[str, JSONValue]:
    """Drop unset optional arguments rather than sending them as null."""
    return {key: value for key, value in kwargs.items() if value is not None}


def get_status_vocabulary(client: PrioMcpClient | None = None) -> StatusVocabulary:
    client = client or get_prio_mcp_client()
    data = client.call_tool("get_status_vocabulary", {})
    return StatusVocabulary.model_validate(data)


def get_priority_board(
    priority_category: str | None = None,
    include_closed: bool = False,
    limit: int = 50,
    cursor: str | None = None,
    client: PrioMcpClient | None = None,
) -> PageEnvelope:
    client = client or get_prio_mcp_client()
    data = client.call_tool(
        "get_priority_board",
        _args(priority_category=priority_category, include_closed=include_closed, limit=limit, cursor=cursor),
    )
    return PageEnvelope.model_validate(data)


def list_employee_tasks(
    employee_id: int,
    include_closed: bool = False,
    updated_since: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    client: PrioMcpClient | None = None,
) -> PageEnvelope:
    client = client or get_prio_mcp_client()
    data = client.call_tool(
        "list_employee_tasks",
        _args(
            employee_id=employee_id,
            include_closed=include_closed,
            updated_since=updated_since,
            limit=limit,
            cursor=cursor,
        ),
    )
    return PageEnvelope.model_validate(data)


def get_task(task_id: int, client: PrioMcpClient | None = None) -> dict[str, JSONValue] | None:
    client = client or get_prio_mcp_client()
    try:
        return client.call_tool("get_task", {"task_id": task_id})
    except PrioNotFoundError:
        return None


def get_status_history(
    from_date: str,
    to_date: str,
    employee_id: int | None = None,
    task_id: int | None = None,
    team_id: int | None = None,
    client: PrioMcpClient | None = None,
) -> StatusHistoryResponse:
    """Exactly one of `employee_id`/`task_id`/`team_id` should be set, per the connector doc."""
    client = client or get_prio_mcp_client()
    data = client.call_tool(
        "get_status_history",
        _args(employee_id=employee_id, task_id=task_id, team_id=team_id, from_date=from_date, to_date=to_date),
    )
    return StatusHistoryResponse.model_validate(data)


def get_assignment_history(
    from_date: str,
    to_date: str,
    task_id: int | None = None,
    employee_id: int | None = None,
    client: PrioMcpClient | None = None,
) -> AssignmentHistoryResponse:
    """`current_assignments` items' `source` distinguishes audit-backed from current-state-only."""
    client = client or get_prio_mcp_client()
    data = client.call_tool(
        "get_assignment_history",
        _args(task_id=task_id, employee_id=employee_id, from_date=from_date, to_date=to_date),
    )
    return AssignmentHistoryResponse.model_validate(data)


def list_teams(client: PrioMcpClient | None = None) -> TeamsResponse:
    client = client or get_prio_mcp_client()
    data = client.call_tool("list_teams", {})
    return TeamsResponse.model_validate(data)


def list_team_members(team_id: int, client: PrioMcpClient | None = None) -> TeamMembersResponse:
    client = client or get_prio_mcp_client()
    data = client.call_tool("list_team_members", {"team_id": team_id})
    return TeamMembersResponse.model_validate(data)


def search_users(
    query: str,
    limit: int = 50,
    cursor: str | None = None,
    client: PrioMcpClient | None = None,
) -> PageEnvelope:
    client = client or get_prio_mcp_client()
    data = client.call_tool("search_users", _args(query=query, limit=limit, cursor=cursor))
    return PageEnvelope.model_validate(data)


def search_tasks(
    query: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    team_id: int | None = None,
    due_before: str | None = None,
    due_after: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    client: PrioMcpClient | None = None,
) -> PageEnvelope:
    client = client or get_prio_mcp_client()
    data = client.call_tool(
        "search_tasks",
        _args(
            query=query,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            team_id=team_id,
            due_before=due_before,
            due_after=due_after,
            limit=limit,
            cursor=cursor,
        ),
    )
    return PageEnvelope.model_validate(data)


def get_task_updates(
    task_id: int,
    limit: int = 50,
    cursor: str | None = None,
    client: PrioMcpClient | None = None,
) -> PageEnvelope:
    client = client or get_prio_mcp_client()
    data = client.call_tool("get_task_updates", _args(task_id=task_id, limit=limit, cursor=cursor))
    return PageEnvelope.model_validate(data)


def get_dashboard_context(team_id: int | None = None, client: PrioMcpClient | None = None) -> DashboardContext:
    client = client or get_prio_mcp_client()
    data = client.call_tool("get_dashboard_context", _args(team_id=team_id))
    return DashboardContext.model_validate(data)


def find_similar_tasks(title: str, client: PrioMcpClient | None = None) -> SimilarTasksResponse:
    client = client or get_prio_mcp_client()
    data = client.call_tool("find_similar_tasks", {"title": title})
    return SimilarTasksResponse.model_validate(data)
