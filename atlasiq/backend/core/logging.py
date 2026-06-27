"""Structured logging configuration for AtlasIQ.

Provides JSON-formatted log output for production and human-readable output for
development. Log level and format are controlled via configuration.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Produces structured logs suitable for log aggregation systems.
    Each log line includes timestamp, level, logger name, message,
    and any extra fields passed via the `extra` parameter.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include any extra fields attached to the log record
        for key in ("document_id", "query_id", "duration_ms", "component"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO", log_format: str = "json") -> None:
    """Configure application-wide logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format — "json" for structured logs, "text" for
            human-readable development output.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured: level=%s, format=%s", level, log_format
    )
