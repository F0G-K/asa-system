"""调度状态机与任务分发策略测试。"""

import uuid
from datetime import UTC, datetime

import pytest
from backend.domain.scheduling.entities import (
    ExecutionStatus,
    RuntimeStage,
    StageName,
)
from backend.domain.scheduling.exceptions import (
    InvalidStageTransition,
    ProjectCancellationRequested,
    StagePrerequisiteNotMet,
)
from backend.domain.scheduling.stage_machine import StageStateMachine
from backend.domain.scheduling.task_policy import TaskDistributionPolicy


def _stage(
    *,
    name: StageName,
    order: int,
    status: ExecutionStatus,
) -> RuntimeStage:
    now = datetime.now(UTC)
    return RuntimeStage(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        runtime_id=uuid.uuid4(),
        stage_name=name,
        stage_order=order,
        stage_status=status,
        started_at=None,
        finished_at=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def test_stage_machine_allows_only_defined_transitions() -> None:
    StageStateMachine.ensure_transition(ExecutionStatus.IDLE, ExecutionStatus.RUNNING)
    StageStateMachine.ensure_transition(ExecutionStatus.RUNNING, ExecutionStatus.SUCCESS)
    StageStateMachine.ensure_transition(ExecutionStatus.RUNNING, ExecutionStatus.FAILED)

    with pytest.raises(InvalidStageTransition):
        StageStateMachine.ensure_transition(
            ExecutionStatus.IDLE,
            ExecutionStatus.SUCCESS,
        )


def test_later_stage_requires_previous_success() -> None:
    stage = _stage(
        name=StageName.CODE_ANALYSIS,
        order=2,
        status=ExecutionStatus.IDLE,
    )
    previous = _stage(
        name=StageName.ENVIRONMENT_SCAN,
        order=1,
        status=ExecutionStatus.RUNNING,
    )

    with pytest.raises(StagePrerequisiteNotMet):
        StageStateMachine.ensure_can_start(
            stage,
            previous_stage=previous,
            stop_requested=False,
        )


def test_stop_requested_rejects_new_stage() -> None:
    with pytest.raises(ProjectCancellationRequested):
        StageStateMachine.ensure_can_start(
            _stage(
                name=StageName.ENVIRONMENT_SCAN,
                order=1,
                status=ExecutionStatus.IDLE,
            ),
            previous_stage=None,
            stop_requested=True,
        )


def test_distribution_policy_releases_dependent_general_after_analysis() -> None:
    assert (
        TaskDistributionPolicy.ready_roles(
            StageName.CODE_ANALYSIS,
            completed_roles=set(),
            existing_roles=set(),
        )[0].worker_role
        == "code_analyst"
    )

    ready = TaskDistributionPolicy.ready_roles(
        StageName.CODE_ANALYSIS,
        completed_roles={"code_analyst"},
        existing_roles={"code_analyst"},
    )
    assert [item.worker_role for item in ready] == ["general"]
