import logging
import sys
from typing import Optional

from app.common.context import get_log_context


class ContextAwareFormatter(logging.Formatter):
    """
    Custom log formatter that includes context information in log messages.
    """

    def format(self, record):
        context = get_log_context()
        original_msg = super().format(record)

        # Add request_id to the log message if available
        if context.get("request_id"):
            return f"[request_id: {context['request_id']}] {original_msg}"

        return original_msg


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration for the application.

    Args:
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to a log file. If provided, logs will be written to this file.
    """
    # Configure log level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Configure handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    # Create formatter
    formatter = ContextAwareFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers and add new ones
    root_logger.handlers.clear()
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: The name of the logger, typically __name__ of the calling module

    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
