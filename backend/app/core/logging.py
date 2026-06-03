"""Structured JSON logging with trace_id — spec non-functional requirement."""
import sys
import uuid
from loguru import logger


def setup_logging(log_level: str = "INFO"):
    logger.remove()
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | {extra[trace_id]} | {message}",
        level=log_level,
        serialize=False,
    )
    logger.add(
        "logs/surveillance_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        format="{time} | {level} | {extra[trace_id]} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        serialize=True,
    )
    logger.configure(extra={"trace_id": "system"})


def get_logger(trace_id: str = None):
    tid = trace_id or str(uuid.uuid4())[:8]
    return logger.bind(trace_id=tid)
