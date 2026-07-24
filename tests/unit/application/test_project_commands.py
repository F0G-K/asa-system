"""项目写用例测试。"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from asa_core.application.commands.create_project import (
    CreateProjectCommand,
    CreateProjectHandler,
)
from asa_core.application.commands.delete_project import (
    DeleteProjectCommand,
    DeleteProjectHandler,
)
from asa_core.application.commands.start_project import (
    StartProjectCommand,
    StartProjectHandler,
)
from asa_core.application.commands.stop_project import (
    StopProjectCommand,
    StopProjectHandler,
)
from asa_core.application.ports.project_repository import (
    ProjectOperationRecord,
    StartProjectResources,
)
from asa_core.domain.projects.entities import Project
from asa_core.domain.projects.exceptions import (
    EnvironmentTypeDisabled,
    IdempotencyKeyReused,
    ProjectNameConfirmationMismatch,
)


def _project(*, status: str = "created") -> Project:
    now = datetime.now(UTC)
    return Project(
        id=uuid.uuid4(),
        project_name="支付服务",
        source_type="repository",
        source_path="https://git.example.com/team/payment.git",
        task_content="检查注入和越权风险",
        environment_type="python-3_12",
        project_status=status,
        created_by=uuid.uuid4(),
        stop_requested_at=None,
        last_started_at=None,
        last_finished_at=None,
        created_at=now,
        updated_at=now,
    )


class TestCreateProjectHandler:
    async def test_create_project(self) -> None:
        repo = AsyncMock()
        repo.get_active_configuration.return_value = ({"python-3_12"}, 2)
        audit = AsyncMock()
        actor_id = uuid.uuid4()

        result = await CreateProjectHandler(audit).handle(
            CreateProjectCommand(
                project_name=" 支付服务 ",
                source_type="repository",
                source_path="https://git.example.com/team/payment.git",
                task_content=" 检查注入和越权风险 ",
                environment_type="python-3_12",
                actor_user_id=actor_id,
                request_id=uuid.uuid4(),
            ),
            project_repo=repo,
        )

        assert result.project_name == "支付服务"
        assert result.created_by == actor_id
        assert result.project_status == "created"
        repo.add.assert_awaited_once_with(result)
        audit.log.assert_awaited_once()

    async def test_disabled_environment_is_rejected(self) -> None:
        repo = AsyncMock()
        repo.get_active_configuration.return_value = (set(), None)
        with pytest.raises(EnvironmentTypeDisabled):
            await CreateProjectHandler(AsyncMock()).handle(
                CreateProjectCommand(
                    project_name="支付服务",
                    source_type="local",
                    source_path="services/payment",
                    task_content="检查权限",
                    environment_type="python-3_12",
                    actor_user_id=uuid.uuid4(),
                    request_id=uuid.uuid4(),
                ),
                project_repo=repo,
            )


class TestStartProjectHandler:
    async def test_start_creates_all_acceptance_records(self) -> None:
        project = _project()
        repo = AsyncMock()
        repo.find_operation.return_value = None
        repo.find_accessible.return_value = project
        repo.has_runtime.return_value = False
        repo.get_active_configuration.return_value = ({"python-3_12"}, 2)
        repo.count_running.return_value = 0
        resources = StartProjectResources(
            runtime_id=uuid.uuid4(),
            first_stage_id=uuid.uuid4(),
            worker_task_id=uuid.uuid4(),
        )
        repo.create_start_resources.return_value = resources

        result = await StartProjectHandler(AsyncMock()).handle(
            StartProjectCommand(
                project_id=project.id,
                actor_user_id=project.created_by,
                actor_is_admin=False,
                request_id=uuid.uuid4(),
                idempotency_key="start-key-001",
            ),
            project_repo=repo,
        )

        assert result.resources == resources
        assert result.replayed is False
        repo.acquire_operation_lock.assert_awaited_once()
        repo.acquire_project_lock.assert_awaited()
        repo.acquire_capacity_lock.assert_awaited_once()
        repo.create_operation.assert_awaited_once()
        repo.append_event.assert_awaited_once()

    async def test_different_key_cannot_create_second_runtime(self) -> None:
        project = _project()
        repo = AsyncMock()
        repo.find_operation.return_value = None
        repo.find_accessible.return_value = project
        repo.has_runtime.return_value = True

        from asa_core.domain.projects.exceptions import ProjectStatusConflict

        with pytest.raises(ProjectStatusConflict):
            await StartProjectHandler(AsyncMock()).handle(
                StartProjectCommand(
                    project_id=project.id,
                    actor_user_id=project.created_by,
                    actor_is_admin=False,
                    request_id=uuid.uuid4(),
                    idempotency_key="start-key-002",
                ),
                project_repo=repo,
            )
        repo.create_start_resources.assert_not_awaited()

    async def test_same_key_replays_first_response(self) -> None:
        project = _project()
        response = {
            "project_id": str(project.id),
            "project_status": "created",
            "operation": "start",
            "accepted_at": datetime.now(UTC).isoformat(),
        }
        repo = AsyncMock()
        from asa_core.application.project_support import build_request_fingerprint

        fingerprint = build_request_fingerprint(
            actor_user_id=project.created_by,
            project_id=project.id,
            operation="start",
            payload={},
        )
        repo.find_operation.return_value = ProjectOperationRecord(
            operation="start",
            request_fingerprint=fingerprint,
            response_data=response,
            accepted_at=datetime.now(UTC),
        )
        result = await StartProjectHandler(AsyncMock()).handle(
            StartProjectCommand(
                project_id=project.id,
                actor_user_id=project.created_by,
                actor_is_admin=False,
                request_id=uuid.uuid4(),
                idempotency_key="start-key-001",
            ),
            project_repo=repo,
        )

        assert result.replayed is True
        assert result.response_data == response
        assert result.resources is None
        repo.create_start_resources.assert_not_awaited()

    async def test_replay_restores_dispatch_resources(self) -> None:
        project = _project()
        resources = StartProjectResources(
            runtime_id=uuid.uuid4(),
            first_stage_id=uuid.uuid4(),
            worker_task_id=uuid.uuid4(),
        )
        response = {
            "project_id": str(project.id),
            "project_status": "created",
            "operation": "start",
            "accepted_at": datetime.now(UTC).isoformat(),
            "_runtime_id": str(resources.runtime_id),
            "_first_stage_id": str(resources.first_stage_id),
            "_worker_task_id": str(resources.worker_task_id),
        }
        repo = AsyncMock()
        from asa_core.application.project_support import build_request_fingerprint

        fingerprint = build_request_fingerprint(
            actor_user_id=project.created_by,
            project_id=project.id,
            operation="start",
            payload={},
        )
        repo.find_operation.return_value = ProjectOperationRecord(
            operation="start",
            request_fingerprint=fingerprint,
            response_data=response,
            accepted_at=datetime.now(UTC),
        )

        result = await StartProjectHandler(AsyncMock()).handle(
            StartProjectCommand(
                project_id=project.id,
                actor_user_id=project.created_by,
                actor_is_admin=False,
                request_id=uuid.uuid4(),
                idempotency_key="start-key-001",
            ),
            project_repo=repo,
        )

        assert result.resources == resources

    async def test_reused_key_for_different_request_is_rejected(self) -> None:
        project = _project()
        repo = AsyncMock()
        repo.find_operation.return_value = ProjectOperationRecord(
            operation="delete",
            request_fingerprint="f" * 64,
            response_data={},
            accepted_at=datetime.now(UTC),
        )
        with pytest.raises(IdempotencyKeyReused):
            await StartProjectHandler(AsyncMock()).handle(
                StartProjectCommand(
                    project_id=project.id,
                    actor_user_id=project.created_by,
                    actor_is_admin=False,
                    request_id=uuid.uuid4(),
                    idempotency_key="start-key-001",
                ),
                project_repo=repo,
            )


class TestStopAndDeleteProjectHandlers:
    async def test_stop_records_cancel_intent(self) -> None:
        project = _project(status="running")
        repo = AsyncMock()
        repo.find_operation.return_value = None
        repo.find_accessible.return_value = project
        repo.set_stop_requested.return_value = True

        result = await StopProjectHandler(AsyncMock()).handle(
            StopProjectCommand(
                project_id=project.id,
                actor_user_id=project.created_by,
                actor_is_admin=False,
                request_id=uuid.uuid4(),
                idempotency_key="stop-key-001",
                reason=" 演示结束\n ",
            ),
            project_repo=repo,
        )

        assert result.replayed is False
        assert result.response_data["project_status"] == "running"
        repo.set_stop_requested.assert_awaited_once()
        repo.create_operation.assert_awaited_once()

    async def test_stop_with_new_key_reuses_existing_cancel_intent(self) -> None:
        project = _project(status="running")
        project.stop_requested_at = datetime.now(UTC)
        repo = AsyncMock()
        repo.find_operation.return_value = None
        repo.find_accessible.return_value = project

        result = await StopProjectHandler(AsyncMock()).handle(
            StopProjectCommand(
                project_id=project.id,
                actor_user_id=project.created_by,
                actor_is_admin=False,
                request_id=uuid.uuid4(),
                idempotency_key="stop-key-002",
                reason=None,
            ),
            project_repo=repo,
        )

        assert result.replayed is True
        assert result.response_data["stop_requested_at"] == (
            project.stop_requested_at.isoformat()
        )
        repo.set_stop_requested.assert_not_awaited()
        repo.append_event.assert_not_awaited()

    async def test_delete_requires_exact_name(self) -> None:
        project = _project(status="completed")
        repo = AsyncMock()
        repo.find_operation.return_value = None
        repo.find_accessible.return_value = project

        with pytest.raises(ProjectNameConfirmationMismatch):
            await DeleteProjectHandler(AsyncMock()).handle(
                DeleteProjectCommand(
                    project_id=project.id,
                    actor_user_id=project.created_by,
                    actor_is_admin=False,
                    request_id=uuid.uuid4(),
                    idempotency_key="delete-key-001",
                    confirm_project_name="支付服务 ",
                ),
                project_repo=repo,
            )
