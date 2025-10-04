import pathlib
import logging

# Get the project root directory
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()

# Define the log configuration directory
LOG_DIR = PROJECT_ROOT / "logs"

# Define the configurations of the logging system
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "afixl.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 5,
            "formatter": "default",
        },
    },
    "loggers": {
        "afixl": {
            "handlers": ["console", "file"],
            "level": logging.INFO,
            "propagate": False,
        },
    },
}
