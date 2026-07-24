"""项目仓储的数据库写入顺序回归测试。"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from backend.domain.projects.entities import Project
from backend.infrastructure.database.project_repository import SqlAlchemyProjectRepository


async def test_project_repository_flushes_project_before_audit_write() -> None:
    session = AsyncMock()
    repository = SqlAlchemyProjectRepository(session)
    now = datetime.now(UTC)
    project = Project(
        id=uuid.uuid4(),
        project_name="测试项目",
        source_type="local",
        source_path="fixtures/demo-app",
        task_content="执行安全评估",
        environment_type="python-3_12",
        project_status="created",
        created_by=uuid.uuid4(),
        stop_requested_at=None,
        last_started_at=None,
        last_finished_at=None,
        created_at=now,
        updated_at=now,
    )

    await repository.add(project)

    session.add.assert_called_once()
    session.flush.assert_awaited_once_with()
