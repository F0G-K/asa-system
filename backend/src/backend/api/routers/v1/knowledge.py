"""知识库路由。

GET    /api/v1/knowledge/entries          — 知识条目列表（分页）
POST   /api/v1/knowledge/entries          — 创建知识条目
GET    /api/v1/knowledge/entries/{id}     — 知识条目详情
PUT    /api/v1/knowledge/entries/{id}     — 更新知识条目（乐观锁）
DELETE /api/v1/knowledge/entries/{id}     — 删除知识条目
POST   /api/v1/knowledge/search           — 语义搜索（关键词匹配）
GET    /api/v1/projects/{id}/knowledge/retrievals — 检索历史
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from backend.api.bootstrap import get_service_container
from backend.api.dependencies import CurrentUser, get_current_user
from backend.api.middleware.request_id import get_request_id
from backend.api.schemas.common import ApiResponse
from backend.domain.auth.exceptions import AdminRequired
from backend.infrastructure.database.models import KnowledgeEntryModel, KnowledgeRetrievalModel
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import asc, desc, func, select

router = APIRouter(tags=["知识库"])


# ─── 请求 Schema ──────────────────────────────────────────────


class CreateKnowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=256)
    content_text: str = Field(min_length=1)
    knowledge_type: str = Field(pattern=r"^(vulnerability_pattern|security_standard|remediation_advice|historical_assessment)$")
    language: str | None = Field(default=None, max_length=32)
    framework: str | None = Field(default=None, max_length=64)
    risk_level: str | None = Field(default=None, pattern=r"^(critical|high|medium|low|info)$")
    tags: list[str] = Field(default_factory=list)
    source_type: str = Field(default="manual", pattern=r"^(manual|external_import|auto_curated)$")
    source_url: str | None = Field(default=None, max_length=2048)


class UpdateKnowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=256)
    content_text: str | None = Field(default=None, min_length=1)
    knowledge_type: str | None = Field(default=None, pattern=r"^(vulnerability_pattern|security_standard|remediation_advice|historical_assessment)$")
    language: str | None = None
    framework: str | None = None
    risk_level: str | None = Field(default=None, pattern=r"^(critical|high|medium|low|info)$")
    tags: list[str] | None = None
    entry_status: str | None = Field(default=None, pattern=r"^(active|disabled|draft)$")
    source_url: str | None = None
    expected_version: int = Field(ge=1)


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_text: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=50)
    knowledge_types: list[str] | None = None
    language: str | None = None
    risk_level: str | None = None
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)


# ─── 工具 ────────────────────────────────────────────────────


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    return ApiResponse[Any](
        code=code, message=message, data=data, request_id=get_request_id(request),
    ).model_dump(mode="json")


def _require_admin(current_user: CurrentUser) -> None:
    if not current_user.is_admin:
        raise AdminRequired()


def _to_summary(e: KnowledgeEntryModel) -> dict[str, Any]:
    return {
        "id": str(e.id), "title": e.title, "knowledge_type": e.knowledge_type,
        "language": e.language, "framework": e.framework,
        "risk_level": e.risk_level, "tags": list(e.tags or []),
        "entry_status": e.entry_status, "source_type": e.source_type,
        "version": e.version, "created_at": e.created_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
    }


def _to_detail(e: KnowledgeEntryModel) -> dict[str, Any]:
    return {
        **_to_summary(e),
        "content_text": e.content_text, "source_url": e.source_url,
        "created_by": str(e.created_by) if e.created_by else None,
        "reviewed_by": str(e.reviewed_by) if e.reviewed_by else None,
        "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None,
    }


# ─── CRUD 路由 ───────────────────────────────────────────────


@router.get("/entries")
async def list_knowledge_entries(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    knowledge_type: str | None = None,
    entry_status: str | None = None,
    risk_level: str | None = None,
    language: str | None = None,
    keyword: str | None = Query(default=None, max_length=128),
    tags: str | None = Query(default=None, description="逗号分隔"),
    sort: str = Query(default="updated_at:desc", pattern=r"^(created_at|updated_at):(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions: list[Any] = []
        if knowledge_type:
            conditions.append(KnowledgeEntryModel.knowledge_type == knowledge_type)
        if entry_status:
            conditions.append(KnowledgeEntryModel.entry_status == entry_status)
        if risk_level:
            conditions.append(KnowledgeEntryModel.risk_level == risk_level)
        if language:
            conditions.append(KnowledgeEntryModel.language == language)
        if keyword:
            escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(
                (KnowledgeEntryModel.title.ilike(f"%{escaped}%", escape="\\"))
                | (KnowledgeEntryModel.content_text.ilike(f"%{escaped}%", escape="\\"))
            )
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            if tag_list:
                conditions.append(KnowledgeEntryModel.tags.overlap(tag_list))

        count_stmt = select(func.count(KnowledgeEntryModel.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = int((await session.execute(count_stmt)).scalar_one())

        sort_field, sort_dir = sort.split(":")
        order_col = getattr(KnowledgeEntryModel, sort_field)
        order_fn = asc if sort_dir == "asc" else desc

        stmt = select(KnowledgeEntryModel)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(order_fn(order_col), asc(KnowledgeEntryModel.id))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await session.execute(stmt)).scalars().all()

    has_next = page * page_size < total
    content = _ok("KNOWLEDGE_LIST_OK", "查询成功",
                   {"items": [_to_summary(r) for r in rows], "page": page, "page_size": page_size,
                    "total": total, "has_next": has_next}, request)
    return JSONResponse(status_code=200, content=content)


@router.post("/entries", status_code=201)
async def create_knowledge_entry(
    request: Request,
    body: CreateKnowledgeRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    _require_admin(current_user)

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            entry = KnowledgeEntryModel(
                id=uuid.uuid4(),
                title=body.title, content_text=body.content_text,
                knowledge_type=body.knowledge_type,
                language=body.language, framework=body.framework,
                risk_level=body.risk_level,
                tags=list(body.tags or []),
                entry_status="active",
                source_type=body.source_type, source_url=body.source_url,
                version=1, created_by=current_user.id,
                created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
            )
            session.add(entry)

        # 重新读取
        result = await session.execute(
            select(KnowledgeEntryModel).where(KnowledgeEntryModel.id == entry.id)
        )
        created = result.scalar_one()

    content = _ok("KNOWLEDGE_CREATED", "知识条目创建成功", _to_detail(created), request)
    return JSONResponse(status_code=201, content=content)


@router.get("/entries/{entry_id}")
async def get_knowledge_entry(
    request: Request,
    entry_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        result = await session.execute(
            select(KnowledgeEntryModel).where(KnowledgeEntryModel.id == entry_id)
        )
        entry = result.scalar_one_or_none()

    if entry is None:
        content = _ok("KNOWLEDGE_NOT_FOUND", "知识条目不存在", None, request)
        return JSONResponse(status_code=404, content=content)

    content = _ok("KNOWLEDGE_DETAIL_OK", "查询成功", _to_detail(entry), request)
    return JSONResponse(status_code=200, content=content)


@router.put("/entries/{entry_id}")
async def update_knowledge_entry(
    request: Request,
    entry_id: uuid.UUID,
    body: UpdateKnowledgeRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    _require_admin(current_user)

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(KnowledgeEntryModel)
                .where(KnowledgeEntryModel.id == entry_id)
                .with_for_update()
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                content = _ok("KNOWLEDGE_NOT_FOUND", "知识条目不存在", None, request)
                return JSONResponse(status_code=404, content=content)

            if entry.version != body.expected_version:
                content = ApiResponse[Any](
                    code="ENTRY_VERSION_CONFLICT",
                    message="条目已被其他管理员更新，请关闭后重新打开编辑",
                    data={"expected_version": body.expected_version, "current_version": entry.version},
                    request_id=get_request_id(request),
                ).model_dump(mode="json")
                return JSONResponse(status_code=409, content=content)

            if body.title is not None:
                entry.title = body.title
            if body.content_text is not None:
                entry.content_text = body.content_text
            if body.knowledge_type is not None:
                entry.knowledge_type = body.knowledge_type
            if body.language is not None:
                entry.language = body.language
            if body.framework is not None:
                entry.framework = body.framework
            if body.risk_level is not None:
                entry.risk_level = body.risk_level
            if body.tags is not None:
                entry.tags = list(body.tags)
            if body.entry_status is not None:
                entry.entry_status = body.entry_status
            if body.source_url is not None:
                entry.source_url = body.source_url
            entry.version = entry.version + 1
            entry.updated_at = datetime.now(UTC)

        # 重新读取
        result = await session.execute(
            select(KnowledgeEntryModel).where(KnowledgeEntryModel.id == entry_id)
        )
        updated = result.scalar_one()

    content = _ok("KNOWLEDGE_UPDATED", "知识条目更新成功", _to_detail(updated), request)
    return JSONResponse(status_code=200, content=content)


@router.delete("/entries/{entry_id}")
async def delete_knowledge_entry(
    request: Request,
    entry_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    _require_admin(current_user)

    container = get_service_container(request.app)
    async with container.session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(KnowledgeEntryModel).where(KnowledgeEntryModel.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                content = _ok("KNOWLEDGE_NOT_FOUND", "知识条目不存在", None, request)
                return JSONResponse(status_code=404, content=content)

            await session.delete(entry)

    content = _ok("KNOWLEDGE_DELETED", "知识条目已删除", None, request)
    return JSONResponse(status_code=200, content=content)


# ─── 搜索 ────────────────────────────────────────────────────


def _simple_similarity(query: str, text: str) -> float:
    """简单关键词匹配相似度计算（无 pgvector 时的 fallback）。"""
    if not query or not text:
        return 0.0
    query_lower = query.lower()
    text_lower = text.lower()
    # 完全匹配
    if query_lower in text_lower:
        return 0.85
    # 单词匹配
    query_words = set(query_lower.split())
    text_words = set(text_lower.split())
    if not query_words:
        return 0.0
    overlap = len(query_words & text_words)
    return min(0.7, overlap / len(query_words) * 0.7)


@router.post("/search")
async def search_knowledge(
    request: Request,
    body: KnowledgeSearchRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions = [KnowledgeEntryModel.entry_status == "active"]
        searched_types = list(body.knowledge_types) if body.knowledge_types else [
            "vulnerability_pattern", "security_standard", "remediation_advice", "historical_assessment"
        ]
        conditions.append(KnowledgeEntryModel.knowledge_type.in_(searched_types))
        if body.language:
            conditions.append(KnowledgeEntryModel.language == body.language)
        if body.risk_level:
            conditions.append(KnowledgeEntryModel.risk_level == body.risk_level)

        stmt = select(KnowledgeEntryModel).where(*conditions)
        rows = (await session.execute(stmt)).scalars().all()

    # 计算相似度并排序
    scored = []
    for r in rows:
        sim = _simple_similarity(body.query_text, f"{r.title} {r.content_text}")
        if sim >= body.min_similarity:
            scored.append((sim, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: body.top_k]

    items = [
        {
            "entry_id": str(r.id), "title": r.title, "knowledge_type": r.knowledge_type,
            "content_text": r.content_text[:2000], "risk_level": r.risk_level,
            "tags": list(r.tags or []), "similarity": round(sim, 4),
        }
        for sim, r in top
    ]

    data = {
        "items": items, "query_text": body.query_text,
        "searched_knowledge_types": searched_types,
        "total_scanned": len(rows), "total_matched": len(items),
    }
    content = _ok("KNOWLEDGE_SEARCH_OK", "搜索完成", data, request)
    return JSONResponse(status_code=200, content=content)


# ─── 检索历史 ────────────────────────────────────────────────


@router.get("/retrievals", include_in_schema=False)
async def _redirect_retrievals():
    """此路由在 main.py 注册到 /api/v1/projects/{project_id}/knowledge/retrievals"""
    ...


router_retrievals = APIRouter(tags=["知识库-检索历史"])


@router_retrievals.get("/{project_id}/knowledge/retrievals")
async def list_knowledge_retrievals(
    request: Request,
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    stage_id: uuid.UUID | None = None,
    worker_task_id: uuid.UUID | None = None,
    retrieval_type: str | None = Query(default=None, pattern=r"^(stage_pre|role_pre|tool_triggered)$"),
    sort: str = Query(default="created_at:desc", pattern=r"^(created_at):(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        conditions: list[Any] = [KnowledgeRetrievalModel.project_id == project_id]
        if stage_id:
            conditions.append(KnowledgeRetrievalModel.stage_id == stage_id)
        if worker_task_id:
            conditions.append(KnowledgeRetrievalModel.worker_task_id == worker_task_id)
        if retrieval_type:
            conditions.append(KnowledgeRetrievalModel.retrieval_type == retrieval_type)

        count_stmt = select(func.count(KnowledgeRetrievalModel.id)).where(*conditions)
        total = int((await session.execute(count_stmt)).scalar_one())

        sort_field, sort_dir = sort.split(":")
        order_col = getattr(KnowledgeRetrievalModel, sort_field)
        order_fn = asc if sort_dir == "asc" else desc

        stmt = (
            select(KnowledgeRetrievalModel)
            .where(*conditions)
            .order_by(order_fn(order_col))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await session.execute(stmt)).scalars().all()

    has_next = page * page_size < total
    items = [
        {
            "id": r.id, "stage_id": str(r.stage_id) if r.stage_id else None,
            "worker_task_id": str(r.worker_task_id) if r.worker_task_id else None,
            "retrieval_type": r.retrieval_type, "query_text": r.query_text,
            "filter_language": r.filter_language,
            "filter_knowledge_types": r.filter_knowledge_types,
            "top_k": r.top_k,
            "retrieved_entries": r.retrieved_entries or [],
            "top_score": r.top_score, "avg_score": r.avg_score,
            "retrieval_duration_ms": r.retrieval_duration_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    data = {"items": items, "page": page, "page_size": page_size, "total": total, "has_next": has_next}
    content = _ok("RETRIEVALS_OK", "查询成功", data, request)
    return JSONResponse(status_code=200, content=content)
