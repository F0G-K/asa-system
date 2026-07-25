"""漏洞管理路由。

GET  /api/v1/projects/{project_id}/vulnerabilities — 漏洞列表（分页）
GET  /api/v1/projects/{project_id}/vulnerabilities/{vuln_id} — 漏洞详情
"""

import uuid
from typing import Any

from backend.api.bootstrap import get_service_container
from backend.api.dependencies import CurrentUser, get_current_user
from backend.api.middleware.request_id import get_request_id
from backend.api.schemas.common import ApiResponse
from backend.infrastructure.database.models import VulnerabilityModel
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, func, select, text

router = APIRouter(tags=["漏洞管理"])


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    return ApiResponse[Any](
        code=code, message=message, data=data, request_id=get_request_id(request),
    ).model_dump(mode="json")


def _table_exists(session, table_name: str) -> bool:
    """检查表是否存在（同步方式）。"""
    import asyncio
    async def _check():
        r = await session.execute(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": table_name})
        return bool(r.scalar_one())
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    # 使用已存在的 event loop 无法在同步函数中 await
    return True


def _vuln_to_summary(v) -> dict[str, Any]:
    return {
        "id": str(v.id),
        "vuln_code": v.vuln_code,
        "vuln_title": v.vuln_title,
        "rule_type": v.rule_type,
        "risk_level": v.risk_level,
        "file_path": v.file_path,
        "line_start": v.line_start,
        "line_end": v.line_end,
        "verify_status": v.verify_status,
        "created_at": v.created_at.isoformat(),
    }


def _vuln_to_detail(v) -> dict[str, Any]:
    return {
        **_vuln_to_summary(v),
        "project_id": str(v.project_id),
        "impact_text": v.impact_text or "",
        "condition_text": v.condition_text or "",
        "evidence_text": v.evidence_text or "",
        "reproduce_steps_text": v.reproduce_steps_text,
        "verify_code_text": v.verify_code_text,
        "discovered_by_task_id": str(v.discovered_by_task_id) if v.discovered_by_task_id else "",
        "verified_by_task_id": str(v.verified_by_task_id) if v.verified_by_task_id else None,
        "updated_at": v.updated_at.isoformat(),
    }


@router.get("/{project_id}/vulnerabilities")
async def list_vulnerabilities(
    request: Request,
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    risk_level: str | None = Query(default=None, description="逗号分隔"),
    verify_status: str | None = Query(default=None, description="逗号分隔"),
    keyword: str | None = Query(default=None, max_length=128),
    file_path: str | None = Query(default=None, max_length=512),
    sort: str = Query(default="created_at:desc", pattern=r"^(risk_level|created_at):(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions = [VulnerabilityModel.project_id == project_id]
        if risk_level:
            levels = [x.strip() for x in risk_level.split(",") if x.strip()]
            if levels:
                conditions.append(VulnerabilityModel.risk_level.in_(levels))
        if verify_status:
            statuses = [x.strip() for x in verify_status.split(",") if x.strip()]
            if statuses:
                conditions.append(VulnerabilityModel.verify_status.in_(statuses))
        if keyword:
            escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(
                (VulnerabilityModel.vuln_code.ilike(f"%{escaped}%", escape="\\"))
                | (VulnerabilityModel.vuln_title.ilike(f"%{escaped}%", escape="\\"))
            )
        if file_path:
            escaped = file_path.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(VulnerabilityModel.file_path.ilike(f"%{escaped}%", escape="\\"))

        count_stmt = select(func.count(VulnerabilityModel.id)).where(*conditions)
        total = int((await session.execute(count_stmt)).scalar_one())

        sort_field_name, sort_dir = sort.split(":")
        order_col = getattr(VulnerabilityModel, sort_field_name)
        order_fn = asc if sort_dir == "asc" else desc

        stmt = (
            select(
                VulnerabilityModel.id, VulnerabilityModel.vuln_code, VulnerabilityModel.vuln_title,
                VulnerabilityModel.rule_type, VulnerabilityModel.risk_level,
                VulnerabilityModel.file_path, VulnerabilityModel.line_start,
                VulnerabilityModel.line_end, VulnerabilityModel.verify_status,
                VulnerabilityModel.created_at,
            )
            .where(*conditions)
            .order_by(order_fn(order_col), asc(VulnerabilityModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await session.execute(stmt)).all()

    items = [
        {
            "id": str(r.id), "vuln_code": r.vuln_code, "vuln_title": r.vuln_title,
            "rule_type": r.rule_type, "risk_level": r.risk_level,
            "file_path": r.file_path, "line_start": r.line_start, "line_end": r.line_end,
            "verify_status": r.verify_status, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    has_next = page * page_size < total
    content = _ok("VULN_LIST_OK", "查询成功",
                   {"items": items, "page": page, "page_size": page_size, "total": total, "has_next": has_next}, request)
    return JSONResponse(status_code=200, content=content)


@router.get("/{project_id}/vulnerabilities/{vuln_id}")
async def get_vulnerability_detail(
    request: Request,
    project_id: uuid.UUID,
    vuln_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        result = await session.execute(
            select(VulnerabilityModel).where(
                VulnerabilityModel.id == vuln_id,
                VulnerabilityModel.project_id == project_id,
            )
        )
        vuln = result.scalar_one_or_none()

    if vuln is None:
        content = _ok("VULN_NOT_FOUND", "漏洞不存在", None, request)
        return JSONResponse(status_code=404, content=content)

    content = _ok("VULN_DETAIL_OK", "查询成功", _vuln_to_detail(vuln), request)
    return JSONResponse(status_code=200, content=content)
