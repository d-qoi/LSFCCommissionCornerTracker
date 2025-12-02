import logging
from logging.handlers import RotatingFileHandler
import os

_logger: logging.Logger | None = None


def configure_logging(level: str = "INFO", logfile: str | None = None):
    """
    Configure global logging for the entire application.

    Parameters
    ----------
    level : str
        Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    logfile : str | None
        If provided, log output will also be written to this file.
        If None, only stdout logging will be used.

    Returns
    -------
    logging.Logger
        The configured root logger.
    """

    global _logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.root.handlers.clear()

    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if logfile:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)

        file_handler = RotatingFileHandler(
            logfile,
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _logger = logger


def get_logger(name: str) -> logging.Logger:
    global _logger

    if _logger is None:
        raise Exception("Logger is not initialized")

    return logging.getLogger(name)
