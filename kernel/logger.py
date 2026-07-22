"""Structured Logging"""
from typing import Any, Dict
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import sys
import traceback


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def to_int(self) -> int:
        return {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }[self.value]


class StructuredLogger:
    """Structured JSON logger"""

    def __init__(self, name: str = "ck-nexus", level: LogLevel = LogLevel.INFO, log_dir: str = None):
        self._name = name
        self._level = level
        self._log_dir = log_dir
        self._extra: Dict[str, Any] = {}

        self._logger = logging.getLogger(name)
        self._logger.setLevel(level.to_int())
        self._logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(console_handler)

        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path / f"{name}.log")
            file_handler.setFormatter(logging.Formatter('%(message)s'))
            self._logger.addHandler(file_handler)

    def get_logger(self, name: str) -> "StructuredLogger":
        child = StructuredLogger(
            name=f"{self._name}.{name}",
            level=self._level,
            log_dir=self._log_dir,
        )
        child._extra = dict(self._extra)
        return child

    def with_fields(self, **kwargs) -> "StructuredLogger":
        self._extra.update(kwargs)
        return self

    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def _log(self, level: LogLevel, message: str, **kwargs):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "logger": self._name,
            "message": message,
            **self._extra,
            **kwargs,
        }
        if "exc_info" in kwargs and kwargs["exc_info"]:
            record["traceback"] = traceback.format_exc()

        self._logger.log(level.to_int(), json.dumps(record, default=str))

    def set_level(self, level: LogLevel):
        self._level = level
        self._logger.setLevel(level.to_int())
