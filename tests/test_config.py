"""Tests for configuration loading."""

import os
from importlib import reload

import pytest

from astronmcp import config as config_module
from astronmcp import spark_client as spark_client_module


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Clear Spark-related env vars before each test."""
    for key in [
        "SPARK_MODE",
        "SPARK_API_PASSWORD",
        "SPARK_API_KEY",
        "SPARK_APP_ID",
        "SPARK_API_SECRET",
        "SPARK_API_URL",
        "SPARK_WS_URL",
        "SPARK_DEFAULT_MODEL",
        "SPARK_MAX_CONTEXT_CHARS",
        "SPARK_MAX_TOKENS",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_coding_defaults():
    os.environ["SPARK_MODE"] = "coding"
    os.environ["SPARK_API_PASSWORD"] = "key"
    reload(config_module)
    settings = config_module.load_settings()
    config_module.validate_settings(settings)

    assert settings.mode == "coding"
    assert "maas-coding-api" in settings.api_url
    assert settings.default_model == "astron-code-latest"
    assert settings.max_context_chars == 96000
    assert settings.max_tokens == 8192


def test_http_defaults():
    os.environ["SPARK_MODE"] = "http"
    os.environ["SPARK_API_PASSWORD"] = "pwd"
    reload(config_module)
    settings = config_module.load_settings()
    config_module.validate_settings(settings)

    assert settings.mode == "http"
    assert "spark-api-open" in settings.api_url
    assert settings.default_model == "4.0Ultra"


def test_websocket_defaults():
    os.environ["SPARK_MODE"] = "websocket"
    os.environ["SPARK_APP_ID"] = "appid"
    os.environ["SPARK_API_KEY"] = "apikey"
    os.environ["SPARK_API_SECRET"] = "secret"
    reload(config_module)
    settings = config_module.load_settings()
    config_module.validate_settings(settings)

    assert settings.mode == "websocket"
    assert settings.app_id == "appid"
    assert settings.api_key == "apikey"
    assert settings.api_secret == "secret"


def test_coding_missing_key():
    os.environ["SPARK_MODE"] = "coding"
    reload(config_module)
    settings = config_module.load_settings()
    with pytest.raises(RuntimeError, match="SPARK_API_PASSWORD"):
        config_module.validate_settings(settings)


def test_client_factory():
    os.environ["SPARK_MODE"] = "coding"
    os.environ["SPARK_API_PASSWORD"] = "key"
    reload(config_module)
    reload(spark_client_module)
    settings = config_module.load_settings()
    config_module.validate_settings(settings)
    client = spark_client_module.create_client(settings)
    assert isinstance(client, spark_client_module.HttpSparkClient)
