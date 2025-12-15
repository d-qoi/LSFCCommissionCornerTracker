from cctracker.server.config import config
from cctracker.log import configure_logging

configure_logging(config.log_level, config.log_file)

from cctracker.server.core import app


__all__ = ["app"]
