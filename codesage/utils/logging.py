import logging
import sys
import structlog


def setup_logging(log_level="INFO", json_logs=False):
    """
    Configures logging for the application.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
    ]

    if json_logs:
        processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level_value, stream=sys.stdout)


def get_logger(name):
    return structlog.get_logger(name)
