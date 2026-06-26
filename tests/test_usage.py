"""Tests for usage normalization across providers."""

from coding_bridge_mcp.api_client import _normalize_usage


def test_normalize_none_and_empty():
    assert _normalize_usage(None) is None
    assert _normalize_usage({}) is None


def test_normalize_volcengine_style():
    """Volcengine Ark / OpenAI-compatible: cached lives under prompt_tokens_details."""
    raw = {
        "prompt_tokens": 120,
        "completion_tokens": 45,
        "total_tokens": 165,
        "prompt_tokens_details": {"cached_tokens": 80},
    }
    out = _normalize_usage(raw)
    assert out == {
        "prompt_tokens": 120,
        "completion_tokens": 45,
        "total_tokens": 165,
        "cached_tokens": 80,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }


def test_normalize_xfyun_top_level_cached():
    """Older xfyun responses may expose cached_tokens at the top level."""
    raw = {
        "prompt_tokens": 50,
        "completion_tokens": 10,
        "total_tokens": 60,
        "cached_tokens": 50,
    }
    out = _normalize_usage(raw)
    assert out is not None
    assert out["cached_tokens"] == 50


def test_normalize_fills_total_when_missing():
    raw = {"prompt_tokens": 7, "completion_tokens": 3}
    out = _normalize_usage(raw)
    assert out is not None
    assert out["total_tokens"] == 10


def test_normalize_handles_garbage_fields():
    """Non-numeric or missing fields must not raise."""
    raw = {
        "prompt_tokens": None,
        "completion_tokens": "bad",
        "total_tokens": 0,
        "prompt_tokens_details": "not-a-dict",
    }
    out = _normalize_usage(raw)
    assert out is not None
    assert out["prompt_tokens"] == 0
    assert out["completion_tokens"] == 0
    assert out["cached_tokens"] == 0