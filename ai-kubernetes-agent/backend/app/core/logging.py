import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Forward standard-library logs to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        logger.opt(exception=record.exc_info).log(record.levelname, record.getMessage())


def configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(sys.stdout, level=level.upper(), serialize=False)
    logging.basicConfig(handlers=[InterceptHandler()], level=level.upper(), force=True)
