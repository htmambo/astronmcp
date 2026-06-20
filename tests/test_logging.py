"""Tests for structured JSON logging."""

import io
import json
import logging

import pytest

from coding_bridge_mcp.logging_config import JSONFormatter, StructuredLogger, configure_logging


@pytest.fixture
def capture_log_stream(monkeypatch):
    """Configure logging to write JSON into a captured StringIO."""
    stream = io.StringIO()
    root = logging.getLogger()
    # Remove any existing handlers to keep the capture clean.
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    yield stream
    root.removeHandler(handler)


def test_json_formatter_includes_extra_fields(capture_log_stream):
    logger = StructuredLogger("test.json")
    logger.info("hello", tool="chat", session_id="abc-123")

    raw = capture_log_stream.getvalue()
    record = json.loads(raw.strip())

    assert record["message"] == "hello"
    assert record["level"] == "INFO"
    assert record["logger"] == "test.json"
    assert record["tool"] == "chat"
    assert record["session_id"] == "abc-123"
    assert "timestamp" in record


def test_configure_logging_is_idempotent():
    # A second call should not add another handler.
    configure_logging("DEBUG")
    before = len(logging.getLogger().handlers)
    configure_logging("DEBUG")
    after = len(logging.getLogger().handlers)
    assert before == after
