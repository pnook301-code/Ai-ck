import json
import pytest
from kernel.logger import StructuredLogger, LogLevel


class TestLogLevel:
    def test_to_int_debug(self):
        assert LogLevel.DEBUG.to_int() == 10

    def test_to_int_info(self):
        assert LogLevel.INFO.to_int() == 20

    def test_to_int_warning(self):
        assert LogLevel.WARNING.to_int() == 30

    def test_to_int_error(self):
        assert LogLevel.ERROR.to_int() == 40

    def test_to_int_critical(self):
        assert LogLevel.CRITICAL.to_int() == 50

    def test_values(self):
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestStructuredLogger:
    def test_default_level(self):
        logger = StructuredLogger(name="test")
        assert logger._level == LogLevel.INFO

    def test_debug_logging(self, capsys):
        logger = StructuredLogger(name="test", level=LogLevel.DEBUG)
        logger.debug("debug message")
        captured = capsys.readouterr()
        assert "debug message" in captured.out

    def test_info_logging(self, capsys):
        logger = StructuredLogger(name="test")
        logger.info("info message")
        captured = capsys.readouterr()
        assert "info message" in captured.out

    def test_warning_logging(self, capsys):
        logger = StructuredLogger(name="test")
        logger.warning("warning message")
        captured = capsys.readouterr()
        assert "warning message" in captured.out

    def test_error_logging(self, capsys):
        logger = StructuredLogger(name="test")
        logger.error("error message")
        captured = capsys.readouterr()
        assert "error message" in captured.out

    def test_critical_logging(self, capsys):
        logger = StructuredLogger(name="test")
        logger.critical("critical message")
        captured = capsys.readouterr()
        assert "critical message" in captured.out

    def test_log_output_is_json(self, capsys):
        logger = StructuredLogger(name="test")
        logger.info("hello")
        captured = capsys.readouterr()
        record = json.loads(captured.out.strip())
        assert record["level"] == "INFO"
        assert record["message"] == "hello"
        assert record["logger"] == "test"
        assert "timestamp" in record

    def test_log_with_extra_fields(self, capsys):
        logger = StructuredLogger(name="test")
        logger.info("event", user="admin", action="login")
        captured = capsys.readouterr()
        record = json.loads(captured.out.strip())
        assert record["user"] == "admin"
        assert record["action"] == "login"

    def test_with_fields(self, capsys):
        logger = StructuredLogger(name="test")
        logger.with_fields(service="kernel").info("started")
        captured = capsys.readouterr()
        record = json.loads(captured.out.strip())
        assert record["service"] == "kernel"

    def test_get_child_logger(self, capsys):
        parent = StructuredLogger(name="parent")
        child = parent.get_logger("child")
        child.info("from child")
        captured = capsys.readouterr()
        lines = [l for l in captured.out.strip().split('\n') if l]
        record = json.loads(lines[-1])
        assert record["logger"] == "parent.child"

    def test_set_level(self, capsys):
        logger = StructuredLogger(name="test", level=LogLevel.ERROR)
        logger.info("should not appear")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_file_logging(self, temp_dir):
        import os
        logger = StructuredLogger(name="file_test", log_dir=temp_dir)
        logger.info("file log")
        log_path = os.path.join(temp_dir, "file_test.log")
        assert os.path.exists(log_path)
        with open(log_path) as f:
            content = f.read()
        assert "file log" in content
