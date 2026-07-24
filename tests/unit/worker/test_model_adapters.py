"""模型与 LangGraph 适配器测试。"""

from backend.application.ports.model_port import ModelPort, ModelRequest, ModelResult
from backend.worker.agents.langgraph_adapter import LangGraphModelAdapter


class FakeModel(ModelPort):
    async def complete(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            content={"summary": "ok"},
            summary="ok",
            prompt_tokens=2,
            completion_tokens=1,
        )

    def estimate_tokens(self, text: str) -> int:
        return len(text)

    async def health_check(self) -> bool:
        return True


async def test_langgraph_adapter_keeps_model_result_and_delegates_health() -> None:
    adapter = LangGraphModelAdapter(FakeModel())
    request = ModelRequest(
        system_prompt="system",
        user_prompt="task",
        context={},
        tools=(),
        output_schema={"type": "object"},
    )

    result = await adapter.complete(request)

    assert result.summary == "ok"
    assert await adapter.health_check() is True
    assert adapter.estimate_tokens("abc") == 3
