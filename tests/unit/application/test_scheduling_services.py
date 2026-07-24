"""调度应用服务纯逻辑测试。"""

import random

from asa_core.application.services.retry_policy import TaskRetryPolicy
from asa_core.application.services.sensitive_text import redact_sensitive_text
from asa_core.domain.agents.exceptions import ModelCallFailed
from asa_core.domain.scheduling.exceptions import SchedulingConflict


def test_retry_policy_retries_only_transient_failures() -> None:
    policy = TaskRetryPolicy(
        max_retries=3,
        backoff_base_seconds=2,
        random_source=random.Random(7),
    )

    transient = policy.decide(TimeoutError(), retries=1)
    assert transient.retry is True
    assert 3 <= transient.countdown_seconds <= 5

    assert policy.decide(SchedulingConflict(), retries=0).retry is False
    assert (
        policy.decide(
            ModelCallFailed("invalid", retryable=False),
            retries=0,
        ).retry
        is False
    )
    assert policy.decide(TimeoutError(), retries=3).retry is False


def test_sensitive_text_redacts_credentials_and_controls_length() -> None:
    value = "password=plain-secret token:abc123456789\x00 tail"
    result = redact_sensitive_text(value, max_length=80)

    assert result is not None
    assert "plain-secret" not in result
    assert "abc123456789" not in result
    assert "[REDACTED]" in result
