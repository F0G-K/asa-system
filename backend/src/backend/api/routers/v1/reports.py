"""报告路由。

GET  /api/v1/projects/{project_id}/report          — 获取报告内容
GET  /api/v1/projects/{project_id}/report/download — 下载报告文件（blob）
"""

import uuid
from typing import Any

from backend.api.bootstrap import get_service_container
from backend.api.dependencies import CurrentUser, get_current_user
from backend.api.middleware.request_id import get_request_id
from backend.api.schemas.common import ApiResponse
from backend.infrastructure.database.models import ReportModel
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import desc, select

router = APIRouter(tags=["报告"])


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    return ApiResponse[Any](
        code=code, message=message, data=data, request_id=get_request_id(request),
    ).model_dump(mode="json")


def _report_to_dict(r: ReportModel) -> dict[str, Any]:
    return {
        "id": str(r.id), "project_id": str(r.project_id),
        "version": r.version, "report_status": r.report_status,
        "report_markdown": r.report_markdown, "report_html": r.report_html,
        "download_available": r.download_available,
        "content_sha256": r.content_sha256, "error_message": r.error_message,
        "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat(),
    }


@router.get("/{project_id}/report")
async def get_report(
    request: Request,
    project_id: uuid.UUID,
    version: int | None = Query(default=None, ge=1),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        stmt = select(ReportModel).where(ReportModel.project_id == project_id)
        if version is not None:
            stmt = stmt.where(ReportModel.version == version)
        else:
            stmt = stmt.order_by(desc(ReportModel.version))
        result = await session.execute(stmt.limit(1))
        report = result.scalar_one_or_none()

    if report is None:
        content = _ok("REPORT_NOT_FOUND", "报告不存在", None, request)
        return JSONResponse(status_code=404, content=content)

    content = _ok("REPORT_OK", "查询成功", _report_to_dict(report), request)
    return JSONResponse(status_code=200, content=content)


@router.get("/{project_id}/report/download")
async def download_report(
    request: Request,
    project_id: uuid.UUID,
    format: str = Query(default="markdown", pattern=r"^(markdown|html)$"),
    version: int | None = Query(default=None, ge=1),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        stmt = select(ReportModel).where(ReportModel.project_id == project_id)
        if version is not None:
            stmt = stmt.where(ReportModel.version == version)
        else:
            stmt = stmt.order_by(desc(ReportModel.version))
        result = await session.execute(stmt.limit(1))
        report = result.scalar_one_or_none()

    if report is None:
        return JSONResponse(status_code=404, content={"code": "REPORT_NOT_FOUND", "message": "报告不存在"})

    if format == "html":
        content = report.report_html or ""
        media_type = "text/html"
        ext = "html"
    else:
        content = report.report_markdown or ""
        media_type = "text/markdown; charset=utf-8"
        ext = "md"

    filename = f"asa-report-{project_id}-v{report.version}.{ext}"
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
