from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

LOG_DIR = Path("backend/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(console)

    rotating = RotatingFileHandler(str(LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    rotating.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(rotating)

    return logger
