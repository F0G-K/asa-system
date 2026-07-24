"""API 启动配置和认证入口中间件测试。"""

from unittest.mock import patch

import pytest
from backend.api.main import create_app
from backend.api.startup import ApiApplication, ApiStartupSettings
from fastapi.testclient import TestClient


def test_startup_settings_use_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ASA_API_HOST",
        "ASA_API_PORT",
        "ASA_API_RELOAD",
        "ASA_API_WORKERS",
        "ASA_API_LOG_LEVEL",
    ):
        monkeypatch.delenv(name, raising=False)

    assert ApiStartupSettings.from_env() == ApiStartupSettings()


def test_startup_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASA_API_HOST", "0.0.0.0")
    monkeypatch.setenv("ASA_API_PORT", "9000")
    monkeypatch.setenv("ASA_API_RELOAD", "true")
    monkeypatch.setenv("ASA_API_WORKERS", "1")
    monkeypatch.setenv("ASA_API_LOG_LEVEL", "debug")

    assert ApiStartupSettings.from_env() == ApiStartupSettings(
        host="0.0.0.0",
        port=9000,
        reload=True,
        workers=1,
        log_level="debug",
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ASA_API_PORT", "0"),
        ("ASA_API_PORT", "not-a-port"),
        ("ASA_API_RELOAD", "sometimes"),
        ("ASA_API_LOG_LEVEL", "verbose"),
    ],
)
def test_startup_settings_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError):
        ApiStartupSettings.from_env()


def test_startup_settings_reject_reload_with_multiple_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASA_API_RELOAD", "true")
    monkeypatch.setenv("ASA_API_WORKERS", "2")

    with pytest.raises(ValueError, match="must be 1"):
        ApiStartupSettings.from_env()


def test_application_passes_settings_to_uvicorn() -> None:
    settings = ApiStartupSettings(host="0.0.0.0", port=9000, log_level="debug")

    with patch("backend.api.startup.uvicorn.run") as run:
        with pytest.raises(SystemExit, match="0"):
            ApiApplication(settings).run()

    run.assert_called_once_with(
        "backend.api.main:app",
        host="0.0.0.0",
        port=9000,
        reload=False,
        workers=1,
        log_level="debug",
    )


def test_anonymous_auth_endpoints_are_not_blocked_by_csrf() -> None:
    app = create_app()

    with TestClient(app, raise_server_exceptions=False) as client:
        init_response = client.post("/api/v1/system/init", json={})
        login_response = client.post("/api/v1/system/login", json={})

    assert init_response.status_code == 422
    assert init_response.json()["code"] == "VALIDATION_ERROR"
    assert login_response.status_code == 422
    assert login_response.json()["code"] == "VALIDATION_ERROR"


def test_protected_write_endpoint_still_requires_csrf() -> None:
    app = create_app()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/system/logout")

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"


def test_success_response_serializes_request_id_as_json() -> None:
    app = create_app()
    app.state.container = object()

    from backend.api.routers.v1.auth import _ok
    from starlette.requests import Request

    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    response = _ok("TEST_OK", "成功", None, request)

    assert isinstance(response["request_id"], str)
