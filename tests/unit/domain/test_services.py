"""认证/授权领域服务测试。"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from backend.domain.auth.entities import User
from backend.domain.auth.exceptions import (
    AccountDisabled,
    AdminRequired,
    InvalidCredentials,
)
from backend.domain.auth.services import AuthenticationService, AuthorizationPolicy


class TestAuthenticationService:
    """AuthenticationService 测试。"""

    @pytest.fixture
    def active_user(self) -> User:
        return User(
            id=uuid.uuid4(),
            username="testuser",
            password_hash="correct_hash",
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
            password_hash="correct_hash",
            role="user",
            status="disabled",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def hasher(self):
        h = AsyncMock()
        h.verify.return_value = True
        return h

    async def test_authenticate_success(self, active_user, hasher) -> None:
        """密码正确且账户激活 → 无异常。"""
        service = AuthenticationService()
        await service.authenticate(active_user, "correct", hasher)

    async def test_authenticate_wrong_password(self, active_user, hasher) -> None:
        """密码错误 → InvalidCredentials。"""
        hasher.verify.return_value = False
        service = AuthenticationService()
        with pytest.raises(InvalidCredentials):
            await service.authenticate(active_user, "wrong", hasher)

    async def test_authenticate_disabled_account(self, disabled_user, hasher) -> None:
        """账户禁用 → 即使密码正确也抛 AccountDisabled。"""
        service = AuthenticationService()
        with pytest.raises(AccountDisabled):
            await service.authenticate(disabled_user, "correct", hasher)


class TestAuthorizationPolicy:
    """AuthorizationPolicy 测试。"""

    @pytest.fixture
    def admin_user(self) -> User:
        return User(
            id=uuid.uuid4(),
            username="admin",
            password_hash="hash",
            role="admin",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def normal_user(self) -> User:
        return User(
            id=uuid.uuid4(),
            username="user",
            password_hash="hash",
            role="user",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_require_admin_admin(self, admin_user) -> None:
        """管理员通过 require_admin。"""
        AuthorizationPolicy.require_admin(admin_user)  # no exception

    def test_require_admin_normal(self, normal_user) -> None:
        """普通用户 require_admin 抛 AdminRequired。"""
        with pytest.raises(AdminRequired):
            AuthorizationPolicy.require_admin(normal_user)

    def test_ensure_active_active(self, normal_user) -> None:
        """激活账户通过 ensure_active。"""
        AuthorizationPolicy.ensure_active(normal_user)  # no exception
