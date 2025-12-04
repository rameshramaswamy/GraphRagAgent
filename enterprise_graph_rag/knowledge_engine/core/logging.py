import sys
import structlog
import logging

def configure_logging():
    """Configures structured JSON logging for production."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Redirect standard logging to structlog
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

logger = structlog.get_logger()