"""攻击路径路由。

GET  /api/v1/projects/{project_id}/attack-paths — 攻击路径列表（分页）
GET  /api/v1/projects/{project_id}/attack-paths/{path_id} — 攻击路径详情（含步骤）
"""

import uuid
from typing import Any

from backend.api.bootstrap import get_service_container
from backend.api.dependencies import CurrentUser, get_current_user
from backend.api.middleware.request_id import get_request_id
from backend.api.schemas.common import ApiResponse
from backend.infrastructure.database.models import (
    AttackPathModel,
    AttackPathStepModel,
    VulnerabilityModel,
)
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import aliased

router = APIRouter(tags=["攻击路径"])


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    return ApiResponse[Any](
        code=code, message=message, data=data, request_id=get_request_id(request),
    ).model_dump(mode="json")


@router.get("/{project_id}/attack-paths")
async def list_attack_paths(
    request: Request,
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=128),
    sort: str = Query(default="created_at:desc", pattern=r"^(created_at):(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions = [AttackPathModel.project_id == project_id]
        if keyword:
            escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(
                (AttackPathModel.path_title.ilike(f"%{escaped}%", escape="\\"))
                | (AttackPathModel.path_summary.ilike(f"%{escaped}%", escape="\\"))
            )

        count_stmt = select(func.count(AttackPathModel.id)).where(*conditions)
        total = int((await session.execute(count_stmt)).scalar_one())

        sort_field, sort_dir = sort.split(":")
        order_col = getattr(AttackPathModel, sort_field)
        order_fn = asc if sort_dir == "asc" else desc

        stmt = (
            select(AttackPathModel)
            .where(*conditions)
            .order_by(order_fn(order_col), asc(AttackPathModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await session.execute(stmt)).scalars().all()

    items = [
        {
            "id": str(r.id), "path_code": r.path_code, "path_title": r.path_title,
            "path_summary": r.path_summary, "final_impact_text": r.final_impact_text,
            "step_count": r.step_count,
            "vulnerability_codes": list(r.vulnerability_codes or []),
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    has_next = page * page_size < total
    content = _ok("PATH_LIST_OK", "查询成功",
                   {"items": items, "page": page, "page_size": page_size, "total": total, "has_next": has_next}, request)
    return JSONResponse(status_code=200, content=content)


@router.get("/{project_id}/attack-paths/{path_id}")
async def get_attack_path_detail(
    request: Request,
    project_id: uuid.UUID,
    path_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        result = await session.execute(
            select(AttackPathModel).where(
                AttackPathModel.id == path_id,
                AttackPathModel.project_id == project_id,
            )
        )
        path = result.scalar_one_or_none()

        if path is None:
            content = _ok("PATH_NOT_FOUND", "攻击路径不存在", None, request)
            return JSONResponse(status_code=404, content=content)

        # 获取步骤及关联的漏洞信息
        steps_result = await session.execute(
            select(AttackPathStepModel)
            .where(AttackPathStepModel.path_id == path_id)
            .order_by(AttackPathStepModel.step_order)
        )
        step_models = steps_result.scalars().all()

        # 批量获取关联漏洞
        vuln_ids = [s.vuln_id for s in step_models if s.vuln_id]
        vuln_map: dict[uuid.UUID, Any] = {}
        if vuln_ids:
            vulns_result = await session.execute(
                select(VulnerabilityModel).where(VulnerabilityModel.id.in_(vuln_ids))
            )
            for v in vulns_result.scalars().all():
                vuln_map[v.id] = {
                    "id": str(v.id), "vuln_code": v.vuln_code, "vuln_title": v.vuln_title,
                    "risk_level": v.risk_level, "verify_status": v.verify_status,
                }

    steps = []
    for s in step_models:
        step_data = {"step_order": s.step_order, "step_text": s.step_text}
        if s.vuln_id and s.vuln_id in vuln_map:
            step_data["vulnerability"] = vuln_map[s.vuln_id]
        else:
            step_data["vulnerability"] = None
        steps.append(step_data)

    detail = {
        "id": str(path.id),
        "project_id": str(path.project_id),
        "path_code": path.path_code,
        "path_title": path.path_title,
        "path_summary": path.path_summary,
        "final_impact_text": path.final_impact_text,
        "steps": steps,
        "created_at": path.created_at.isoformat(),
    }
    content = _ok("PATH_DETAIL_OK", "查询成功", detail, request)
    return JSONResponse(status_code=200, content=content)
