import logging
from logging.handlers import RotatingFileHandler
import os
import sys


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

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.root.handlers.clear()
    logging.root.setLevel(numeric_level)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logging.root.addHandler(console_handler)
    
    if logfile:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        file_handler = RotatingFileHandler(
            logfile, maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logging.root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
