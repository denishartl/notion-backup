# ABOUTME: Tests for structured JSON log formatter.
# ABOUTME: Verifies field names, value formats, and exception handling.

import json
import logging
import re
import sys

import pytest

from notion_backup.logging_config import JsonLogFormatter


def make_record(
    name="app.test",
    level=logging.INFO,
    msg="hello",
    args=(),
    exc_info=None,
):
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=args,
        exc_info=exc_info,
    )
    return record


class TestJsonLogFormatter:
    def setup_method(self):
        self.formatter = JsonLogFormatter()

    def test_output_is_valid_json(self):
        record = make_record()
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_normal_record_has_exactly_four_keys(self):
        record = make_record()
        parsed = json.loads(self.formatter.format(record))
        assert set(parsed.keys()) == {"timestamp", "level", "msg", "logger"}

    @pytest.mark.parametrize("level,expected", [
        (logging.WARNING, "warning"),
        (logging.INFO, "info"),
        (logging.ERROR, "error"),
    ])
    def test_level_is_lowercase(self, level, expected):
        record = make_record(level=level)
        parsed = json.loads(self.formatter.format(record))
        assert parsed["level"] == expected

    def test_timestamp_precision(self):
        record = make_record()
        record.created = 1716892799.9005
        parsed = json.loads(self.formatter.format(record))
        assert parsed["timestamp"].endswith(".900Z"), (
            f"timestamp {parsed['timestamp']!r} should end with .900Z"
        )

    def test_timestamp_format(self):
        record = make_record()
        parsed = json.loads(self.formatter.format(record))
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
        assert re.match(pattern, parsed["timestamp"]), (
            f"timestamp {parsed['timestamp']!r} does not match expected format"
        )

    def test_msg_interpolates_args(self):
        record = make_record(msg="%s done", args=("backup",))
        parsed = json.loads(self.formatter.format(record))
        assert parsed["msg"] == "backup done"

    def test_msg_no_args(self):
        record = make_record(msg="simple message")
        parsed = json.loads(self.formatter.format(record))
        assert parsed["msg"] == "simple message"

    def test_logger_name(self):
        record = make_record(name="notion_backup.scheduler")
        parsed = json.loads(self.formatter.format(record))
        assert parsed["logger"] == "notion_backup.scheduler"

    def test_exception_record_includes_exc_info_key(self):
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = make_record(exc_info=exc_info)
        parsed = json.loads(self.formatter.format(record))
        assert "exc_info" in parsed

    def test_exception_record_exc_info_contains_traceback(self):
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = make_record(exc_info=exc_info)
        parsed = json.loads(self.formatter.format(record))
        assert "ValueError" in parsed["exc_info"]
        assert "test error" in parsed["exc_info"]

    def test_exception_record_still_has_base_keys(self):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            exc_info = sys.exc_info()

        record = make_record(exc_info=exc_info)
        parsed = json.loads(self.formatter.format(record))
        assert {"timestamp", "level", "msg", "logger"}.issubset(parsed.keys())

    def test_no_exception_no_exc_info_key(self):
        record = make_record()
        parsed = json.loads(self.formatter.format(record))
        assert "exc_info" not in parsed
