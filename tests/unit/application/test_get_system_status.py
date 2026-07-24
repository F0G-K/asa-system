"""系统状态查询 Handler 单元测试。"""

from unittest.mock import AsyncMock

from backend.application.queries.get_system_status import (
    GetSystemStatusHandler,
    GetSystemStatusQuery,
)


class TestGetSystemStatusHandler:
    """GetSystemStatusHandler 测试。"""

    async def test_initialized(self) -> None:
        """存在用户 → 返回 True。"""
        repo = AsyncMock()
        repo.exists_any.return_value = True

        handler = GetSystemStatusHandler()
        result = await handler.handle(GetSystemStatusQuery(), user_repo=repo)

        assert result is True

    async def test_not_initialized(self) -> None:
        """无用户 → 返回 False。"""
        repo = AsyncMock()
        repo.exists_any.return_value = False

        handler = GetSystemStatusHandler()
        result = await handler.handle(GetSystemStatusQuery(), user_repo=repo)

        assert result is False
