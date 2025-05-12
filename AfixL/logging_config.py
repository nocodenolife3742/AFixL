import logging
from logging.handlers import RotatingFileHandler
from AfixL import PROJECT_ROOT


def setup_logging():
    """
    Set up logging configuration.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                PROJECT_ROOT / "afixl.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
            ),
            logging.StreamHandler(),
        ],
    )
