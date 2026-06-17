"""Configuration and subscription detection for iFlytek Spark / Coding Plan."""

from __future__ import annotations

import os
from dataclasses import dataclass


# OpenAI-compatible endpoints for different iFlytek subscription types.
CODING_PLAN_API_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
SPARK_OPEN_API_URL = "https://spark-api-open.xf-yun.com/v1/chat/completions"


@dataclass(frozen=True)
class Settings:
    """Runtime configuration parsed from environment variables."""

    mode: str  # "http" (generic Spark) or "websocket" (native Spark) or "coding" (Coding Plan)
    api_url: str  # HTTP endpoint (full /chat/completions URL)
    api_password: str  # HTTP Bearer token (APIPassword / API key)
    app_id: str  # WebSocket app id
    api_key: str  # WebSocket API key
    api_secret: str  # WebSocket API secret
    ws_url: str  # WebSocket endpoint
    default_model: str
    timeout_seconds: float
    max_context_chars: int
    max_messages: int
    max_tokens: int


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_settings() -> Settings:
    """Load settings from environment variables."""
    mode = _env("SPARK_MODE", "coding").lower().strip()
    if mode not in {"http", "websocket", "coding"}:
        raise ValueError(
            f"SPARK_MODE must be 'coding', 'http' or 'websocket', got '{mode}'"
        )

    api_password = _env("SPARK_API_PASSWORD") or _env("SPARK_API_KEY") or ""
    ws_url = _env(
        "SPARK_WS_URL",
        "wss://spark-api.xf-yun.com/v4.0/chat",
    )

    if mode == "coding":
        default_api_url = _env("SPARK_API_URL", CODING_PLAN_API_URL)
        default_model = _env("SPARK_DEFAULT_MODEL", "astron-code-latest")
        default_max_context = "96000"
        default_max_tokens = "8192"
    elif mode == "http":
        default_api_url = _env("SPARK_API_URL", SPARK_OPEN_API_URL)
        default_model = _env("SPARK_DEFAULT_MODEL", "4.0Ultra")
        default_max_context = "24000"
        default_max_tokens = "4096"
    else:  # websocket
        default_api_url = ""
        default_model = _env("SPARK_DEFAULT_MODEL", "4.0Ultra")
        default_max_context = "24000"
        default_max_tokens = "4096"

    return Settings(
        mode=mode,
        api_url=default_api_url,
        api_password=api_password,
        app_id=_env("SPARK_APP_ID", ""),
        api_key=_env("SPARK_API_KEY", ""),
        api_secret=_env("SPARK_API_SECRET", ""),
        ws_url=ws_url,
        default_model=default_model,
        timeout_seconds=float(_env("SPARK_TIMEOUT_SECONDS", "120")),
        max_context_chars=int(_env("SPARK_MAX_CONTEXT_CHARS", default_max_context)),
        max_messages=int(_env("SPARK_MAX_MESSAGES", "40")),
        max_tokens=int(_env("SPARK_MAX_TOKENS", default_max_tokens)),
    )


def validate_settings(settings: Settings) -> None:
    """Raise a clear error if the selected subscription mode is mis-configured."""
    if settings.mode in {"http", "coding"}:
        if not settings.api_password:
            raise RuntimeError(
                f"{settings.mode.upper()} mode requires SPARK_API_PASSWORD (or SPARK_API_KEY) to be set."
            )
        if not settings.api_url:
            raise RuntimeError(f"{settings.mode.upper()} mode requires SPARK_API_URL to be set.")
    elif settings.mode == "websocket":
        missing = [
            name
            for name, value in {
                "SPARK_APP_ID": settings.app_id,
                "SPARK_API_KEY": settings.api_key,
                "SPARK_API_SECRET": settings.api_secret,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                "WebSocket mode requires all of: " + ", ".join(missing)
            )
