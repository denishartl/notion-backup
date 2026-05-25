# ABOUTME: Structured JSON log formatter for Loki/Grafana ingestion.
# ABOUTME: Emits one JSON object per log record with timestamp, level, msg, logger fields.

import json
import logging
from datetime import datetime, timezone


class JsonLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Fields always present: timestamp, level, msg, logger.
    When exc_info is set, an additional exc_info field contains the formatted traceback.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, timezone.utc)
        timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"

        entry: dict = {
            "timestamp": timestamp,
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)
