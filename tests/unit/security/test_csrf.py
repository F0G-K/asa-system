"""CSRF 工具和安全工具单元测试。"""

from asa_core.infrastructure.security.csrf import generate_csrf_token, verify_csrf_token


class TestCsrf:
    """CSRF Token 工具测试。"""

    def test_generate_token_length(self) -> None:
        """生成的 token 至少有足够长度。"""
        token = generate_csrf_token()
        assert len(token) >= 32  # base64 编码至少 32 字符

    def test_generate_token_unique(self) -> None:
        """连续生成的 token 不重复。"""
        tokens = [generate_csrf_token() for _ in range(10)]
        assert len(set(tokens)) == 10  # 10 个 token 全部不同

    def test_verify_matching(self) -> None:
        """相同 token 校验通过。"""
        token = "abc123token"
        assert verify_csrf_token(token, token) is True

    def test_verify_mismatch(self) -> None:
        """不同 token 校验失败。"""
        assert verify_csrf_token("abc", "xyz") is False

    def test_verify_empty(self) -> None:
        """空字符串比较。"""
        assert verify_csrf_token("", "") is True
        assert verify_csrf_token("a", "") is False
        assert verify_csrf_token("", "b") is False
