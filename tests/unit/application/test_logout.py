"""登出 Handler 单元测试。"""

from unittest.mock import AsyncMock

import pytest
from backend.application.commands.logout import LogoutCommand, LogoutHandler


class TestLogoutHandler:
    """LogoutHandler 测试。"""

    async def test_logout_success(self) -> None:
        """正常退出：调用 session_store.revoke_session。"""
        session_store = AsyncMock()
        handler = LogoutHandler(session_store=session_store)
        command = LogoutCommand(session_token="some_token")

        await handler.handle(command)

        session_store.revoke_session.assert_called_once_with("some_token")

    async def test_logout_idempotent(self) -> None:
        """重复退出不报错（幂等）。"""
        session_store = AsyncMock()
        session_store.revoke_session.return_value = None  # 模拟会话已不存在
        handler = LogoutHandler(session_store=session_store)

        # 第一次
        await handler.handle(LogoutCommand(session_token="token"))
        # 第二次（同 token）
        await handler.handle(LogoutCommand(session_token="token"))

        assert session_store.revoke_session.call_count == 2
