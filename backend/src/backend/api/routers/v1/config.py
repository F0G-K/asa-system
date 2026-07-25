"""系统配置路由。

GET  /api/v1/system/config — 获取当前生效配置
PUT  /api/v1/system/config — 更新配置（乐观锁）
"""

from typing import Any

from backend.api.bootstrap import get_service_container
from backend.api.dependencies import CurrentUser, get_current_user
from backend.api.middleware.request_id import get_request_id
from backend.api.schemas.common import ApiResponse
from backend.domain.auth.exceptions import AdminRequired
from backend.infrastructure.database.models import SystemConfigModel
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

router = APIRouter(tags=["系统配置"])


class UpdateConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int | None = Field(default=None, description="乐观锁版本号，null 则跳过检查")
    default_timeout_seconds: int | None = None
    max_concurrent_projects: int | None = None
    log_retention_days: int | None = None
    file_retention_days: int | None = None
    enabled_environment_types: list[str] = Field(default_factory=list)
    settings: dict[str, Any] | None = None


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    return ApiResponse[Any](
        code=code, message=message, data=data, request_id=get_request_id(request),
    ).model_dump(mode="json")


def _require_admin(current_user: CurrentUser) -> None:
    if not current_user.is_admin:
        raise AdminRequired()


def _config_to_dict(cfg: SystemConfigModel) -> dict[str, Any]:
    return {
        "id": str(cfg.id),
        "version": cfg.version,
        "default_timeout_seconds": cfg.default_timeout_seconds,
        "max_concurrent_projects": cfg.max_concurrent_projects,
        "log_retention_days": cfg.log_retention_days,
        "file_retention_days": cfg.file_retention_days,
        "enabled_environment_types": list(cfg.enabled_environment_types or []),
        "settings": dict(cfg.settings or {}),
        "is_active": cfg.is_active,
        "updated_by": str(cfg.updated_by),
        "updated_at": cfg.updated_at.isoformat(),
    }


@router.get("/config")
async def get_system_config(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """获取当前生效的系统配置。需要管理员权限。"""
    _require_admin(current_user)

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        result = await session.execute(
            select(SystemConfigModel).where(SystemConfigModel.is_active.is_(True)).limit(1)
        )
        cfg = result.scalar_one_or_none()

    if cfg is None:
        content = _ok("CONFIG_NOT_FOUND", "没有生效的系统配置", None, request)
        return JSONResponse(status_code=404, content=content)

    content = _ok("CONFIG_OK", "查询成功", _config_to_dict(cfg), request)
    return JSONResponse(status_code=200, content=content)


@router.put("/config")
async def update_system_config(
    request: Request,
    body: UpdateConfigRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """更新系统配置。需要管理员权限。使用乐观锁防并发冲突。"""
    _require_admin(current_user)

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(SystemConfigModel)
                .where(SystemConfigModel.is_active.is_(True))
                .with_for_update()
                .limit(1)
            )
            cfg = result.scalar_one_or_none()
            if cfg is None:
                content = _ok("CONFIG_NOT_FOUND", "没有生效的系统配置", None, request)
                return JSONResponse(status_code=404, content=content)

            if body.expected_version is not None and cfg.version != body.expected_version:
                content = ApiResponse[Any](
                    code="CONFIG_VERSION_CONFLICT",
                    message="配置已被其他管理员更新，请刷新后重试",
                    data={"expected_version": body.expected_version, "current_version": cfg.version},
                    request_id=get_request_id(request),
                ).model_dump(mode="json")
                return JSONResponse(status_code=409, content=content)

            new_version = cfg.version + 1
            values: dict[str, Any] = {"version": new_version, "updated_by": current_user.id}
            if body.default_timeout_seconds is not None:
                values["default_timeout_seconds"] = body.default_timeout_seconds
            if body.max_concurrent_projects is not None:
                values["max_concurrent_projects"] = body.max_concurrent_projects
            if body.log_retention_days is not None:
                values["log_retention_days"] = body.log_retention_days
            if body.file_retention_days is not None:
                values["file_retention_days"] = body.file_retention_days
            if body.enabled_environment_types:
                values["enabled_environment_types"] = body.enabled_environment_types
            if body.settings is not None:
                values["settings"] = body.settings

            await session.execute(
                update(SystemConfigModel).where(SystemConfigModel.id == cfg.id).values(**values)
            )

        # 读取更新后的配置
        result = await session.execute(
            select(SystemConfigModel).where(SystemConfigModel.id == cfg.id)
        )
        updated_cfg = result.scalar_one()

    content = _ok("CONFIG_UPDATED", "系统配置已更新", _config_to_dict(updated_cfg), request)
    return JSONResponse(status_code=200, content=content)
