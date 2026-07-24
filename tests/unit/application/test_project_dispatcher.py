"""项目受理后的消息投递测试。"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from asa_api.project_dispatcher import ApiProjectTaskDispatcher
from asa_core.application.ports.project_repository import StartProjectResources
from asa_core.domain.projects.exceptions import DependencyUnavailable


async def test_start_dispatches_first_stage_after_commit() -> None:
    """启动受理只投递首个阶段的标识消息。"""

    adapter = AsyncMock()
    resources = StartProjectResources(
        runtime_id=uuid.uuid4(),
        first_stage_id=uuid.uuid4(),
        worker_task_id=uuid.uuid4(),
    )
    project_id = uuid.uuid4()
    request_id = uuid.uuid4()

    with patch(
        "asa_api.project_dispatcher.CeleryApiStageDispatcher",
        return_value=adapter,
    ):
        await ApiProjectTaskDispatcher().dispatch_start(
            project_id=project_id,
            resources=resources,
            request_id=request_id,
            idempotency_key="start-key-001",
        )

    message = adapter.dispatch_stage.await_args.args[0]
    assert message.project_id == project_id
    assert message.stage_id == resources.first_stage_id
    assert message.request_id == request_id
    assert message.schema_version == 1


async def test_start_maps_broker_failure_to_dependency_error() -> None:
    adapter = AsyncMock()
    adapter.dispatch_stage.side_effect = RuntimeError("broker unavailable")
    resources = StartProjectResources(
        runtime_id=uuid.uuid4(),
        first_stage_id=uuid.uuid4(),
        worker_task_id=uuid.uuid4(),
    )

    with (
        patch(
            "asa_api.project_dispatcher.CeleryApiStageDispatcher",
            return_value=adapter,
        ),
        pytest.raises(DependencyUnavailable),
    ):
        await ApiProjectTaskDispatcher().dispatch_start(
            project_id=uuid.uuid4(),
            resources=resources,
            request_id=uuid.uuid4(),
            idempotency_key="start-key-001",
        )
