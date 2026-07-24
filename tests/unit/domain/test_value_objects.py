"""Username/PasswordHash 值对象单元测试。"""

import pytest
from asa_core.domain.auth.value_objects import PasswordHash, Username


class TestUsername:
    """Username 值对象测试。"""

    def test_valid_username(self) -> None:
        """合法用户名通过校验并自动转小写。"""
        u = Username("  Security_Admin  ")
        assert u.value == "security_admin"

    def test_too_short(self) -> None:
        """长度小于 3 时抛异常。"""
        with pytest.raises(ValueError, match="长度必须在 3-64"):
            Username("ab")

    def test_too_long(self) -> None:
        """长度超过 64 时抛异常。"""
        with pytest.raises(ValueError, match="长度必须在 3-64"):
            Username("a" * 65)

    def test_whitespace_in_middle(self) -> None:
        """用户名中间含空白抛异常。"""
        with pytest.raises(ValueError, match="不得包含空白"):
            Username("hello world")

    def test_exact_min_length(self) -> None:
        """恰好 3 字符通过校验。"""
        u = Username("abc")
        assert u.value == "abc"

    def test_exact_max_length(self) -> None:
        """恰好 64 字符通过校验。"""
        u = Username("a" * 64)
        assert len(u.value) == 64

    def test_str_representation(self) -> None:
        """__str__ 返回用户名。"""
        u = Username("Admin")
        assert str(u) == "admin"


class TestPasswordHash:
    """PasswordHash 值对象测试。"""

    def test_valid_hash(self) -> None:
        """合法哈希字符串通过校验。"""
        h = PasswordHash("$argon2id$v=19$m=65536,t=3,p=4$salt$hash12345")
        assert isinstance(h.value, str)

    def test_empty_hash_raises(self) -> None:
        """空哈希抛异常。"""
        with pytest.raises(ValueError):
            PasswordHash("")

    def test_too_short_hash_raises(self) -> None:
        """过短哈希抛异常。"""
        with pytest.raises(ValueError):
            PasswordHash("1234567890123456789")  # 19 chars < 20
