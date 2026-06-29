"""Live smoke test against the Volcano Engine Ark Coding Plan endpoint.

This test is **opt-in**: it is skipped unless pytest is invoked with
``-m volcengine_live``. By default the rest of the suite stays hermetic
(matching the project's stated policy of "no API fees from tests").

Run with::

    pytest -m volcengine_live tests/test_volcengine_live.py -v

When ``-v`` is set the test prints a verbose, redacted trace of the live
HTTP round-trip (request payload + response body). All API keys are
redacted before printing — only the first/last 4 characters remain.

Requires ``PROVIDER=volcengine-coding`` and ``API_KEY=<ark-key>`` in the
environment (or a project ``.env`` that ``python-dotenv`` will load — but
note that ``load_dotenv(override=False)`` only fills missing keys). The key
is **never** hardcoded in source; if no key is configured the test is
skipped via ``pytest.skip``.
"""
from __future__ import annotations

import json
import os
from importlib import reload

import pytest
from dotenv import load_dotenv

from coding_bridge_mcp import api_client as api_client_module
from coding_bridge_mcp import config as config_module


pytestmark = pytest.mark.volcengine_live


def _load_ark_key() -> str:
    """Resolve the Ark API key from the environment or a project ``.env``.

    Order matches the volcengine-coding credential fallback: ``API_KEY`` →
    ``VOLCENGINE_API_KEY`` → ``ARK_API_KEY``. ``load_dotenv(override=False)``
    fills missing keys from ``.env`` (same behaviour as ``server.py``) so a
    project-local key works without exporting it to the shell.

    Raises ``pytest.skip`` when no key is configured — the live test is opt-in
    by marker, and running it without credentials would only produce a 401.
    """
    load_dotenv(override=False)
    for name in ("API_KEY", "VOLCENGINE_API_KEY", "ARK_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    pytest.skip(
        "volcengine_live requires one of API_KEY / VOLCENGINE_API_KEY / "
        "ARK_API_KEY in the environment or .env"
    )


def _redact_secret(value: str | None) -> str:
    """Return a safe, abbreviated form of a secret for verbose logging.

    Rules:
        * ``None`` or empty        → ``"<unset>"``
        * length < 12              → ``"***"``  (too short to safely truncate)
        * otherwise                → ``"<first4>****<last4>"``

    The original value is never reconstructed from this representation.
    """
    if not value:
        return "<unset>"
    if len(value) < 12:
        return "***"
    return f"{value[:4]}****{value[-4:]}"


def _maybe_verbose(verbose: bool, payload: dict) -> None:
    """Pretty-print ``payload`` to stderr when ``-v`` is active.

    pytest shows stderr from passing tests only when ``-s`` is passed, but
    also surfaces it as a ``Captured stderr call`` block on failure. Using
    stderr (not stdout) keeps the trace separate from any test's real
    return value, and matches the project's own logging convention
    (see ``logging_config.configure_logging``).
    """
    if not verbose:
        return
    # `flush=True` so the trace appears immediately under `-s -v` rather
    # than being held in the buffer until the test ends.
    print(
        json.dumps(payload, ensure_ascii=False, indent=2),
        file=__import__("sys").stderr,
        flush=True,
    )


def _build_volc_settings(monkeypatch):
    """Reload config + api_client modules with PROVIDER=volcengine-coding."""
    for key in [
        "PROVIDER",
        "API_KEY",
        "VOLCENGINE_API_KEY",
        "ARK_API_KEY",
        "SPARK_MODE",
        "SPARK_API_PASSWORD",
        "SPARK_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PROVIDER", "volcengine-coding")
    # Read the Ark key from the environment (never hardcode it in source).
    # _load_ark_key() skips the test when no key is configured.
    monkeypatch.setenv("API_KEY", _load_ark_key())
    reload(config_module)
    reload(api_client_module)
    settings = config_module.load_settings()
    config_module.validate_settings(settings)
    return settings


@pytest.mark.asyncio
async def test_volcengine_end_to_end_smoke(monkeypatch, request):
    """Settings → validate → HttpApiClient → real Ark POST → non-empty reply.

    Verbose request/response trace is printed to stderr when pytest is run
    with ``-v`` (or higher) or with ``-s``. ``request`` is a built-in
    pytest fixture; ``config.option.verbose`` reflects the verbosity flag
    (True under ``-v``/``--verbose``).
    """
    verbose = bool(request.config.option.verbose)
    settings = _build_volc_settings(monkeypatch)

    # --- Local config layer checks (no network yet) ---
    assert settings.provider == "volcengine-coding"
    assert settings.mode == "http"
    assert "ark.cn-beijing.volces.com" in settings.api_url
    assert settings.api_url.endswith("/chat/completions")
    assert settings.default_model == "ark-code-latest"
    assert settings.api_password.startswith("ark-"), (
        "API key does not look like an Ark key"
    )

    client = api_client_module.create_client(settings)
    assert isinstance(client, api_client_module.HttpApiClient)

    messages = [{"role": "user", "content": "用一句话回答：1+1=?"}]

    # ---- Verbose trace: outbound request ----
    _maybe_verbose(
        verbose,
        {
            "stage": "request",
            "url": settings.api_url,
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {_redact_secret(settings.api_password)}",
                "Content-Type": "application/json",
            },
            "payload": {
                "model": settings.default_model,
                "messages": messages,
                "stream": False,
                "temperature": 1.0,
                "max_tokens": settings.max_tokens,
            },
        },
    )

    # --- Real network call ---
    content, usage = await client.call(
        messages=messages,
        model=settings.default_model,
        temperature=1.0,
    )

    # ---- Verbose trace: inbound response (no secrets on the return path) ----
    _maybe_verbose(
        verbose,
        {
            "stage": "response",
            "url": settings.api_url,
            "model_used": settings.default_model,
            "content": content,
            "usage": usage,
        },
    )

    # --- Assertions on the real response ---
    assert isinstance(content, str) and content.strip(), (
        f"empty content from Ark API; usage={usage}"
    )
    assert "2" in content, (
        f"expected the answer to mention '2', got: {content!r}"
    )
    assert isinstance(usage, dict)
    assert usage.get("total_tokens", 0) > 0