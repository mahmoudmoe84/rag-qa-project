"""Tests for the logging configuration."""

import json
import logging
from pathlib import Path

import pytest

from app.utils.logger import LoggerMixin, get_logger, setup_logging


@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file path."""
    log_file = tmp_path / "test.log"
    return str(log_file)


@pytest.fixture
def clean_logging():
    """Clean up logging configuration before and after tests."""
    # Clear any existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    yield

    # Clean up after test
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)


def test_setup_logging_creates_log_directory(temp_log_file, clean_logging):
    """Test that setup_logging creates the log directory if it doesn't exist."""
    log_path = Path(temp_log_file)
    assert not log_path.parent.exists() or len(list(log_path.parent.iterdir())) == 0

    setup_logging(log_level="INFO", log_file_path=temp_log_file)

    assert log_path.parent.exists()


def test_setup_logging_configures_handlers(temp_log_file, clean_logging):
    """Test that setup_logging configures both console and file handlers."""
    setup_logging(log_level="INFO", log_file_path=temp_log_file)

    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 2

    # Check handler types
    handler_types = [type(h).__name__ for h in root_logger.handlers]
    assert "StreamHandler" in handler_types
    assert "FileHandler" in handler_types


def test_setup_logging_sets_log_level(temp_log_file, clean_logging):
    """Test that setup_logging sets the correct log level."""
    setup_logging(log_level="DEBUG", log_file_path=temp_log_file)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_get_logger_returns_structlog_logger(temp_log_file, clean_logging):
    """Test that get_logger returns a structlog logger."""
    setup_logging(log_level="INFO", log_file_path=temp_log_file)

    logger = get_logger("test_module")
    # Check that logger has structlog methods
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'debug')
    assert hasattr(logger, 'warning')
    assert hasattr(logger, 'error')


def test_logger_writes_json_to_file(temp_log_file, clean_logging):
    """Test that logger writes JSON formatted logs to file."""
    setup_logging(log_level="INFO", log_file_path=temp_log_file)

    logger = get_logger("test_module")
    logger.info("Test message", extra_field="extra_value")

    # Force flush
    for handler in logging.getLogger().handlers:
        handler.flush()

    # Read the log file
    log_path = Path(temp_log_file)
    assert log_path.exists()

    log_content = log_path.read_text()
    assert log_content.strip()  # Ensure something was written

    # Parse as JSON
    log_lines = [line for line in log_content.strip().split("\n") if line]
    assert len(log_lines) > 0

    log_entry = json.loads(log_lines[0])
    assert log_entry["event"] == "Test message"
    assert log_entry["level"] == "info"
    assert log_entry["logger"] == "test_module"
    assert "timestamp" in log_entry


def test_logger_mixin():
    """Test the LoggerMixin class."""

    class TestClass(LoggerMixin):
        pass

    instance = TestClass()
    logger = instance.logger

    # Check that logger has structlog methods
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'debug')
    assert hasattr(logger, 'warning')
    assert hasattr(logger, 'error')


def test_multiple_log_levels(temp_log_file, clean_logging):
    """Test logging at different levels."""
    setup_logging(log_level="DEBUG", log_file_path=temp_log_file)

    logger = get_logger("test_module")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Force flush
    for handler in logging.getLogger().handlers:
        handler.flush()

    # Read the log file
    log_path = Path(temp_log_file)
    log_content = log_path.read_text()
    log_lines = [line for line in log_content.strip().split("\n") if line]

    assert len(log_lines) == 4

    # Verify all messages are JSON
    for line in log_lines:
        log_entry = json.loads(line)
        assert "event" in log_entry
        assert "level" in log_entry


def test_third_party_loggers_reduced_noise(temp_log_file, clean_logging):
    """Test that third-party library loggers are set to WARNING level."""
    setup_logging(log_level="INFO", log_file_path=temp_log_file)

    # Check that third-party loggers are set to WARNING
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    assert logging.getLogger("openai").level == logging.WARNING
    assert logging.getLogger("qdrant_client").level == logging.WARNING
    assert logging.getLogger("urllib3").level == logging.WARNING
