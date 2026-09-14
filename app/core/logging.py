import logging
import sys
from datetime import datetime, timezone
from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Formats log records as structured text with distinct operational tags:
    [LLM], [RETRIEVAL], [DB], [ARTIFACT], [API]
    """
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        category = getattr(record, "category", "SYSTEM")
        message = record.getMessage()
        
        base = f"{timestamp} [{record.levelname:<7}] [{category:<9}] {message}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]
    
    # Silence overly verbose external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


logger = logging.getLogger("lenny_assistant")


def log_event(category: str, message: str, level: int = logging.INFO, **extra):
    """Convenience helper to emit categorized operational events."""
    extra_dict = {"category": category}
    if extra:
        message = f"{message} | " + " ".join(f"{k}={v}" for k, v in extra.items())
    logger.log(level, message, extra=extra_dict)
