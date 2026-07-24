"""Worker 依赖组装。"""

import os
from dataclasses import dataclass

from backend.application.commands.cancel_project import CancelProjectHandler
from backend.application.commands.converge_worker_failure import (
    ConvergeWorkerFailureHandler,
)
from backend.application.commands.execute_stage import ExecuteStageHandler
from backend.application.commands.execute_worker import ExecuteWorkerTaskHandler
from backend.application.commands.recover_stale import RecoverStaleTasksHandler
from backend.application.ports.model_port import ModelPort
from backend.application.ports.rag_retriever import NoOpRagRetriever
from backend.application.services.context_assembler import ContextAssembler
from backend.application.services.retry_policy import TaskRetryPolicy
from backend.infrastructure.database.base import async_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.worker.agents.langgraph_adapter import LangGraphModelAdapter
from backend.worker.agents.openai_compatible import OpenAICompatibleModelAdapter
from backend.worker.context_source import SqlAlchemyAgentContextSource
from backend.worker.dispatcher import CeleryStageTaskDispatcher
from backend.worker.model_adapter import ModelAdapterNotConfigured


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    task_max_retries: int
    retry_backoff_base: int
    context_max_tokens: int
    rag_max_result_tokens: int

    @classmethod
    def from_env(cls) -> "WorkerSettings":
        return cls(
            task_max_retries=int(os.getenv("ASA_TASK_MAX_RETRIES", "3")),
            retry_backoff_base=int(os.getenv("ASA_TASK_RETRY_BACKOFF_BASE", "2")),
            context_max_tokens=int(os.getenv("ASA_CONTEXT_MAX_TOKENS", "12000")),
            rag_max_result_tokens=int(os.getenv("ASA_RAG_MAX_RESULT_TOKENS", "2000")),
        )


@dataclass(slots=True)
class WorkerContainer:
    session_factory: async_sessionmaker[AsyncSession]
    dispatcher: CeleryStageTaskDispatcher
    execute_stage_handler: ExecuteStageHandler
    converge_failure_handler: ConvergeWorkerFailureHandler
    cancel_project_handler: CancelProjectHandler
    recover_stale_tasks_handler: RecoverStaleTasksHandler
    retry_policy: TaskRetryPolicy
    settings: WorkerSettings
    model: ModelPort

    def create_worker_handler(self, session: AsyncSession) -> ExecuteWorkerTaskHandler:
        context_assembler = ContextAssembler(
            context_source=SqlAlchemyAgentContextSource(session),
            rag_retriever=NoOpRagRetriever(),
            model=self.model,
            max_tokens=self.settings.context_max_tokens,
            rag_max_tokens=self.settings.rag_max_result_tokens,
        )
        return ExecuteWorkerTaskHandler(
            model=self.model,
            context_assembler=context_assembler,
        )


def create_worker_container() -> WorkerContainer:
    settings = WorkerSettings.from_env()
    model = LangGraphModelAdapter(_create_provider_model())
    return WorkerContainer(
        session_factory=async_session_factory,
        dispatcher=CeleryStageTaskDispatcher(),
        execute_stage_handler=ExecuteStageHandler(),
        converge_failure_handler=ConvergeWorkerFailureHandler(),
        cancel_project_handler=CancelProjectHandler(),
        recover_stale_tasks_handler=RecoverStaleTasksHandler(),
        retry_policy=TaskRetryPolicy(
            max_retries=settings.task_max_retries,
            backoff_base_seconds=settings.retry_backoff_base,
        ),
        settings=settings,
        model=model,
    )


def _create_provider_model() -> ModelPort:
    base_url = os.getenv("ASA_MODEL_BASE_URL")
    api_key = os.getenv("ASA_MODEL_API_KEY")
    model_name = os.getenv("ASA_MODEL_NAME")
    if not base_url or not api_key or not model_name:
        return ModelAdapterNotConfigured()
    return OpenAICompatibleModelAdapter(
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
        timeout_seconds=float(os.getenv("ASA_MODEL_REQUEST_TIMEOUT_SECONDS", "60")),
        max_output_tokens=int(os.getenv("ASA_MODEL_MAX_OUTPUT_TOKENS", "4096")),
    )


container = create_worker_container()
