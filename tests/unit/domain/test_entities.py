"""User 实体单元测试。"""

import uuid
from datetime import datetime, timezone

from backend.domain.auth.entities import User


class TestUserEntity:
    """User 聚合根测试。"""

    def test_create_admin(self) -> None:
        """create_admin 工厂方法正确创建管理员。"""
        admin = User.create_admin(
            username="security_admin",
            password_hash="$argon2id$hash",
        )
        assert isinstance(admin.id, uuid.UUID)
        assert admin.username == "security_admin"
        assert admin.role == "admin"
        assert admin.status == "active"
        assert admin.is_admin is True
        assert admin.is_active is True
        assert isinstance(admin.created_at, datetime)
        assert isinstance(admin.updated_at, datetime)
        # created_at 和 updated_at 应该很接近
        delta = abs((admin.updated_at - admin.created_at).total_seconds())
        assert delta < 1.0

    def test_is_admin_false(self) -> None:
        """普通用户的 is_admin 返回 False。"""
        user = User(
            id=uuid.uuid4(),
            username="normal_user",
            password_hash="hash",
            role="user",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert user.is_admin is False

    def test_is_active_disabled(self) -> None:
        """禁用账户的 is_active 返回 False。"""
        user = User(
            id=uuid.uuid4(),
            username="disabled_user",
            password_hash="hash",
            role="user",
            status="disabled",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert user.is_active is False
