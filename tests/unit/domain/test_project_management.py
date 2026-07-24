"""项目管理领域规则测试。"""

import pytest
from backend.application.project_support import redact_user_text
from backend.domain.projects.exceptions import (
    ProjectDeleteForbidden,
    ProjectNotRunning,
    ProjectStatusConflict,
    SourceCredentialForbidden,
    SourcePathInvalid,
)
from backend.domain.projects.status_machine import ProjectStatusMachine
from backend.domain.projects.validators import SourcePathValidator
from backend.domain.projects.value_objects import EnvironmentType, ProjectName


class TestProjectStatusMachine:
    """项目状态机合法和非法分支。"""

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            ("created", "running"),
            ("created", "failed"),
            ("running", "completed"),
            ("running", "failed"),
            ("running", "stopped"),
        ],
    )
    def test_valid_transitions(self, current: str, target: str) -> None:
        ProjectStatusMachine.ensure_transition(current, target)

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            ("completed", "created"),
            ("failed", "created"),
            ("stopped", "running"),
            ("created", "completed"),
        ],
    )
    def test_invalid_transitions(self, current: str, target: str) -> None:
        with pytest.raises(ProjectStatusConflict):
            ProjectStatusMachine.ensure_transition(current, target)

    def test_stop_requires_running(self) -> None:
        with pytest.raises(ProjectNotRunning):
            ProjectStatusMachine.ensure_can_stop("created")

    def test_running_project_cannot_be_deleted(self) -> None:
        with pytest.raises(ProjectDeleteForbidden):
            ProjectStatusMachine.ensure_can_delete("running")


class TestSourcePathValidator:
    """源码路径和凭证安全测试。"""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("services/payment", "services/payment"),
            ("services//payment", "services/payment"),
            (r"services\payment", "services/payment"),
        ],
    )
    def test_valid_local_path(self, raw: str, expected: str) -> None:
        assert SourcePathValidator.validate("local", raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "/etc/passwd",
            "../secret",
            "services/../../secret",
            r"C:\Windows",
            ".",
        ],
    )
    def test_invalid_local_path(self, raw: str) -> None:
        with pytest.raises(SourcePathInvalid):
            SourcePathValidator.validate("local", raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "https://git.example.com/team/repo.git",
            "ssh://git@git.example.com/team/repo.git",
            "git@git.example.com:team/repo.git",
        ],
    )
    def test_valid_repository(self, raw: str) -> None:
        assert SourcePathValidator.validate("repository", raw) == raw

    @pytest.mark.parametrize(
        "raw",
        [
            "https://user:password@git.example.com/team/repo.git",
            "https://git.example.com/team/repo.git?token=secret",
        ],
    )
    def test_repository_credentials_are_rejected(self, raw: str) -> None:
        with pytest.raises(SourceCredentialForbidden):
            SourcePathValidator.validate("repository", raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "http://git.example.com/team/repo.git",
            "file:///tmp/repo",
            "https://git.example.com",
            "not-a-repository",
        ],
    )
    def test_invalid_repository(self, raw: str) -> None:
        with pytest.raises(SourcePathInvalid):
            SourcePathValidator.validate("repository", raw)


class TestProjectValueObjects:
    """项目名称与环境标识规范化。"""

    def test_project_name_is_trimmed(self) -> None:
        assert ProjectName("  支付服务  ").value == "支付服务"

    def test_project_name_rejects_blank(self) -> None:
        with pytest.raises(ValueError):
            ProjectName("   ")

    def test_environment_type_format(self) -> None:
        assert EnvironmentType("python-3_12").value == "python-3_12"
        with pytest.raises(ValueError):
            EnvironmentType("Python 3.12")

    def test_user_text_redacts_sensitive_assignment(self) -> None:
        assert redact_user_text(
            "停止，token=secret-value",
            max_length=500,
        ) == "停止，token=[REDACTED]"
