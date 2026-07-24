"""AI 角色与工具权限测试。"""

import pytest
from asa_core.domain.agents.exceptions import RoleNotAllowedForStage, ToolNotAllowed
from asa_core.domain.agents.role import RoleRegistry, WorkerRole
from asa_core.domain.agents.tool_permissions import ToolName, ToolPermissionPolicy
from asa_core.domain.scheduling.entities import StageName


def test_rag_is_enabled_only_for_analysis_roles() -> None:
    assert RoleRegistry.get(WorkerRole.CODE_ANALYST).rag_enabled is True
    assert RoleRegistry.get(WorkerRole.VULNERABILITY_VERIFIER).rag_enabled is True
    assert RoleRegistry.get(WorkerRole.REPORT_EDITOR).rag_enabled is False


def test_role_cannot_execute_in_unassigned_stage() -> None:
    with pytest.raises(RoleNotAllowedForStage):
        RoleRegistry.ensure_allowed(
            WorkerRole.REPORT_EDITOR,
            StageName.CODE_ANALYSIS,
        )


def test_model_role_cannot_use_undeclared_command_tool() -> None:
    with pytest.raises(ToolNotAllowed):
        ToolPermissionPolicy.ensure_allowed(
            WorkerRole.CODE_ANALYST,
            ToolName.CONTROLLED_COMMAND,
        )

    ToolPermissionPolicy.ensure_allowed(
        WorkerRole.VULNERABILITY_VERIFIER,
        ToolName.CONTROLLED_COMMAND,
    )
