"""领域异常单元测试。"""

from asa_core.domain.auth.exceptions import (
    AccountDisabled,
    AdminRequired,
    AuthenticationRequired,
    CsrfValidationFailed,
    DomainException,
    InvalidCredentials,
    SessionExpired,
    SystemAlreadyInitialized,
    SystemNotInitialized,
)


class TestDomainExceptions:
    """领域异常测试。"""

    def test_inheritance(self) -> None:
        """所有异常继承自 DomainException。"""
        assert issubclass(InvalidCredentials, DomainException)
        assert issubclass(SystemAlreadyInitialized, DomainException)
        assert issubclass(SystemNotInitialized, DomainException)
        assert issubclass(AccountDisabled, DomainException)
        assert issubclass(AuthenticationRequired, DomainException)
        assert issubclass(SessionExpired, DomainException)
        assert issubclass(CsrfValidationFailed, DomainException)
        assert issubclass(AdminRequired, DomainException)

    def test_default_messages(self) -> None:
        """异常有合理的默认消息。"""
        assert "用户名或密码错误" in str(InvalidCredentials())
        assert "系统已完成初始化" in str(SystemAlreadyInitialized())
        assert "尚未初始化" in str(SystemNotInitialized())

    def test_custom_message(self) -> None:
        """支持自定义消息。"""
        exc = DomainException("custom msg")
        assert str(exc) == "custom msg"
