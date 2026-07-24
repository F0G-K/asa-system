"""AI 执行角色领域模型。"""

from backend.domain.agents.role import RoleDefinition, RoleRegistry, WorkerRole
from backend.domain.agents.tool_permissions import ToolName, ToolPermissionPolicy

__all__ = [
    "RoleDefinition",
    "RoleRegistry",
    "ToolName",
    "ToolPermissionPolicy",
    "WorkerRole",
]
