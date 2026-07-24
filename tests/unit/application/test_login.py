"""登录 Handler 单元测试（使用 mock 依赖）。"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from asa_core.application.commands.login import (
    LoginCommand,
    LoginHandler,
    LoginResult,
)
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import (
    AccountDisabled,
    InvalidCredentials,
    SystemNotInitialized,
)
from asa_core.domain.auth.services import AuthenticationService


class TestLoginHandler:
    """LoginHandler 测试。"""

    @pytest.fixture
    def active_user(self) -> User:
        return User(
            id=uuid.uuid4(),
            username="testuser",
            password_hash="hashed_pw",
            role="user",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def disabled_user(self) -> User:
        return User(
            id=uuid.uuid4(),
            username="disabled",
            password_hash="hashed_pw",
            role="user",
            status="disabled",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def deps(self):
        """构造 mock 依赖。"""
        password_hasher = AsyncMock()
        password_hasher.verify.return_value = True

        session_store = AsyncMock()
        session_store.create_session.return_value = (
            "session_token_xyz",
            "csrf_token_abc",
            datetime.now(timezone.utc) + timedelta(hours=2),
        )

        audit_logger = AsyncMock()
        auth_service = AuthenticationService()

        return {
            "password_hasher": password_hasher,
            "session_store": session_store,
            "audit_logger": audit_logger,
            "auth_service": auth_service,
        }

    @pytest.fixture
    def user_repo(self, active_user):
        repo = AsyncMock()
        repo.exists_any.return_value = True
        repo.find_by_username.return_value = active_user
        return repo

    async def test_login_success(self, deps, user_repo) -> None:
        """正常登录：返回 LoginResult + 会话 token。"""
        handler = LoginHandler(**deps)
        command = LoginCommand(username="testuser", password="correct")

        result = await handler.handle(command, user_repo=user_repo)

        assert isinstance(result, LoginResult)
        assert result.user.username == "testuser"
        assert result.session_token == "session_token_xyz"
        assert result.csrf_token == "csrf_token_abc"
        deps["session_store"].create_session.assert_called_once()
        deps["audit_logger"].log.assert_called()

    async def test_login_system_not_initialized(self, deps) -> None:
        """系统未初始化 → SystemNotInitialized。"""
        handler = LoginHandler(**deps)
        command = LoginCommand(username="any", password="any")

        repo = AsyncMock()
        repo.exists_any.return_value = False  # 系统未初始化

        with pytest.raises(SystemNotInitialized):
            await handler.handle(command, user_repo=repo)

    async def test_login_user_not_found(self, deps) -> None:
        """用户不存在 → InvalidCredentials（且执行假哈希）。"""
        deps["password_hasher"].verify.return_value = False
        handler = LoginHandler(**deps)
        command = LoginCommand(username="ghost", password="any")

        repo = AsyncMock()
        repo.exists_any.return_value = True
        repo.find_by_username.return_value = None  # 用户不存在

        with pytest.raises(InvalidCredentials):
            await handler.handle(command, user_repo=repo)

        # 确认执行了假哈希调用（时序均衡）
        deps["password_hasher"].verify.assert_called()

    async def test_login_wrong_password(self, deps, user_repo) -> None:
        """密码错误 → InvalidCredentials。"""
        deps["password_hasher"].verify.side_effect = [False]  # 假哈希用了一次
        # 实际：用户存在时，authenticate 会再调 verify
        # 但 auth_service 只关心自己的 verify 结果
        deps["password_hasher"].verify.side_effect = None
        deps["password_hasher"].verify.return_value = False

        handler = LoginHandler(**deps)
        command = LoginCommand(username="testuser", password="wrong")

        with pytest.raises(InvalidCredentials):
            await handler.handle(command, user_repo=user_repo)

        # 失败时也应该写审计
        deps["audit_logger"].log.assert_called_with(
            action="login",
            object_type="user",
            result_status="failure",
            actor_user_id=user_repo.find_by_username.return_value.id,
            metadata={"username": "testuser"},
        )

    async def test_login_username_normalized(self, deps) -> None:
        """用户名转为小写后查询。"""
        handler = LoginHandler(**deps)
        repo = AsyncMock()
        repo.exists_any.return_value = True
        repo.find_by_username.return_value = None  # 找不到用户

        command = LoginCommand(username="  Admin  ", password="pwd")

        with pytest.raises(InvalidCredentials):
            await handler.handle(command, user_repo=repo)

        # 确认 repo 收到的是小写规范化后的用户名
        repo.find_by_username.assert_called_with("admin")
