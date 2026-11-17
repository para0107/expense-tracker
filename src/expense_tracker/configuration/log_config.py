import logging

from expense_tracker.configuration.config import LogSettings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def setup_logging(log_settings: LogSettings) -> None:
    logging.basicConfig(level=log_settings.level, format=LOG_FORMAT)
