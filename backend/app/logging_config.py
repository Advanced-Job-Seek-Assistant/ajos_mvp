# app/logging_config.py

import os
import logging
from logging.handlers import TimedRotatingFileHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_BASENAME = os.path.join(LOG_DIR, "backend.log")
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"

def setup_logger():
    logger = logging.getLogger("app.backend")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers in development / reload
    logger.handlers.clear()

    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        LOG_FILE_BASENAME,
        when='midnight',
        interval=1,
        backupCount=14,
        encoding='utf-8',
        utc=True  # Set to False if you prefer local time
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logging with date-based filenames initialized!")
    return logger

# Export the logger instance for use everywhere
logger = setup_logger()
