"""实时监控路由。

GET  /api/v1/projects/{project_id}/messages  — AI 对话消息（游标分页）
GET  /api/v1/projects/{project_id}/logs       — 运行日志（游标分页）
GET  /api/v1/projects/{project_id}/resources  — 资源消耗（游标分页）
"""

import uuid
from typing import Any

from backend.api.bootstrap import get_service_container
from backend.api.dependencies import CurrentUser, get_current_user
from backend.api.middleware.request_id import get_request_id
from backend.api.schemas.common import ApiResponse
from backend.infrastructure.database.models import (
    ChatMessageModel,
    ResourceSampleModel,
    RuntimeLogModel,
)
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, select
from sqlalchemy.sql.expression import ColumnElement

router = APIRouter(tags=["实时监控"])


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    return ApiResponse[Any](
        code=code, message=message, data=data, request_id=get_request_id(request),
    ).model_dump(mode="json")


def _cursor_query(
    model,
    conditions: list[ColumnElement[bool]],
    cursor: int | None,
    limit: int,
    order_col,
    order_dir: str = "asc",
) -> tuple[list[Any], int | None, bool]:
    """通用游标分页查询器，返回 (items, next_cursor, has_more)。"""
    import asyncio

    async def _run(session):
        if cursor is not None:
            if order_dir == "asc":
                conditions.append(order_col > cursor)
            else:
                conditions.append(order_col < cursor)

        stmt = (
            select(model)
            .where(*conditions)
            .order_by(asc(order_col) if order_dir == "asc" else desc(order_col))
            .limit(limit + 1)
        )
        rows = (await session.execute(stmt)).scalars().all()

        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = items[-1].id if items else None
        return items, next_cursor, has_more

    return _run


# ─── messages ────────────────────────────────────────────────


@router.get("/{project_id}/messages")
async def list_messages(
    request: Request,
    project_id: uuid.UUID,
    cursor: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    stage_id: uuid.UUID | None = None,
    worker_role: str | None = None,
    message_type: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions: list[ColumnElement[bool]] = [ChatMessageModel.project_id == project_id]
        if stage_id:
            conditions.append(ChatMessageModel.stage_id == stage_id)
        if worker_role:
            conditions.append(ChatMessageModel.worker_role == worker_role)
        if message_type:
            conditions.append(ChatMessageModel.message_type == message_type)

        fn = _cursor_query(ChatMessageModel, conditions, cursor, limit, ChatMessageModel.id, "asc")
        items, next_cursor, has_more = await fn(session)

    data = {
        "items": [
            {
                "id": m.id, "stage_id": str(m.stage_id),
                "worker_task_id": str(m.worker_task_id) if m.worker_task_id else "",
                "worker_role": m.worker_role, "message_type": m.message_type,
                "message_text": m.message_text, "created_at": m.created_at.isoformat(),
            }
            for m in items
        ],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
    return JSONResponse(status_code=200, content=_ok("MESSAGES_OK", "查询成功", data, request))


# ─── logs ────────────────────────────────────────────────────


@router.get("/{project_id}/logs")
async def list_logs(
    request: Request,
    project_id: uuid.UUID,
    cursor: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    log_level: str | None = Query(default=None, pattern=r"^(debug|info|warning|error)$"),
    stage_id: uuid.UUID | None = None,
    order: str = Query(default="asc", pattern=r"^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions: list[ColumnElement[bool]] = [RuntimeLogModel.project_id == project_id]
        if log_level:
            conditions.append(RuntimeLogModel.log_level == log_level)
        if stage_id:
            conditions.append(RuntimeLogModel.stage_id == stage_id)

        fn = _cursor_query(RuntimeLogModel, conditions, cursor, limit, RuntimeLogModel.id, order)
        items, next_cursor, has_more = await fn(session)

    data = {
        "items": [
            {
                "id": lg.id,
                "stage_id": str(lg.stage_id) if lg.stage_id else None,
                "worker_task_id": str(lg.worker_task_id) if lg.worker_task_id else None,
                "request_id": str(lg.request_id) if lg.request_id else None,
                "log_level": lg.log_level, "log_content": lg.log_content,
                "created_at": lg.created_at.isoformat(),
            }
            for lg in items
        ],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
    return JSONResponse(status_code=200, content=_ok("LOGS_OK", "查询成功", data, request))


# ─── resources ───────────────────────────────────────────────


@router.get("/{project_id}/resources")
async def list_resources(
    request: Request,
    project_id: uuid.UUID,
    cursor: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions: list[ColumnElement[bool]] = [ResourceSampleModel.project_id == project_id]
        fn = _cursor_query(ResourceSampleModel, conditions, cursor, limit, ResourceSampleModel.id, "asc")
        items, next_cursor, has_more = await fn(session)

    data = {
        "items": [
            {
                "id": r.id, "runtime_id": str(r.runtime_id),
                "cpu_usage": r.cpu_usage, "memory_usage": r.memory_usage,
                "token_count": r.token_count, "recorded_at": r.recorded_at.isoformat(),
            }
            for r in items
        ],
        "next_cursor": next_cursor,
        "has_more": has_more,
        "units": {"cpu_usage": "%", "memory_usage": "MB", "token_count": "tokens"},
    }
    return JSONResponse(status_code=200, content=_ok("RESOURCES_OK", "查询成功", data, request))
