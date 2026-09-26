"""Logging setup. Configures the root logger; never logs secrets."""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging. Raises ValueError for an unknown level name."""
    level_name = level.upper()
    if level_name not in logging.getLevelNamesMapping():
        raise ValueError(f"Invalid log level: {level!r}")
    logging.basicConfig(level=level_name, format=LOG_FORMAT, force=True)
