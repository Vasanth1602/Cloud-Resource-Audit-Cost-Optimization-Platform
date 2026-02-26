from __future__ import annotations

import logging
import sys
from typing import Any

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class ContextLogger:
    """Logger that automatically injects context fields into every log record."""

    def __init__(self, name: str, **context: Any) -> None:
        self._logger = logging.getLogger(name)
        self._context = context

    def _log(self, level: str, message: str, **extra: Any) -> None:
        merged = {**self._context, **extra}
        getattr(self._logger, level)(message, extra=merged)

    def info(self, message: str, **extra: Any) -> None:
        self._log("info", message, **extra)

    def warning(self, message: str, **extra: Any) -> None:
        self._log("warning", message, **extra)

    def error(self, message: str, **extra: Any) -> None:
        self._log("error", message, **extra)

    def debug(self, message: str, **extra: Any) -> None:
        self._log("debug", message, **extra)
