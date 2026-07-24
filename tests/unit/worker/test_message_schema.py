"""Celery 消息协议测试。"""

import uuid

import pytest
from backend.worker.message_schema import WorkerTaskPayload
from pydantic import ValidationError


def test_worker_message_rejects_unknown_fields_and_future_version() -> None:
    payload = {
        "project_id": str(uuid.uuid4()),
        "stage_id": str(uuid.uuid4()),
        "worker_task_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "idempotency_key": "stage:worker:request",
        "schema_version": 2,
        "cookie": "must-not-enter-message",
    }

    with pytest.raises(ValidationError):
        WorkerTaskPayload.model_validate(payload)
