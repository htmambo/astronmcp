"""Live smoke test against the Volcano Engine Ark Coding Plan endpoint.

This test is **opt-in**: it is skipped unless pytest is invoked with
``-m volcengine_live``. By default the rest of the suite stays hermetic
(matching the project's stated policy of "no API fees from tests").

Run with::

    pytest -m volcengine_live tests/test_volcengine_live.py -v

Requires ``PROVIDER=volcengine-coding`` and ``API_KEY=<ark-key>`` in the
environment (or a project ``.env`` that ``python-dotenv`` will load — but
note that ``load_dotenv(override=False)`` only fills missing keys).
"""
from __future__ import annotations

import os
from importlib import reload

import pytest

from coding_bridge_mcp import api_client as api_client_module
from coding_bridge_mcp import config as config_module


pytestmark = pytest.mark.volcengine_live


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
    # Project ships a .env with the user's Ark key; set it explicitly so the
    # test does not depend on cwd. `monkeypatch.setenv` overrides any prior
    # value, which is the desired behavior here.
    monkeypatch.setenv("API_KEY", "***REMOVED-ARK-KEY***")
    reload(config_module)
    reload(api_client_module)
    settings = config_module.load_settings()
    config_module.validate_settings(settings)
    return settings


@pytest.mark.asyncio
async def test_volcengine_end_to_end_smoke(monkeypatch):
    """Settings → validate → HttpApiClient → real Ark POST → non-empty reply."""
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

    # --- Real network call ---
    messages = [{"role": "user", "content": "用一句话回答：1+1=?"}]
    content, usage = await client.call(
        messages=messages,
        model=settings.default_model,
        temperature=1.0,
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