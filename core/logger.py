"""
core/logger.py
---------------
Tüm modüllerin ortak logger'ı. Konsola ve logs/rifki.log dosyasına yazar.
Hiçbir modül kullanıcıya çıplak traceback göstermemeli; hatalar buraya loglanır,
kullanıcıya sadeleştirilmiş mesaj gösterilir.
"""

import logging
from pathlib import Path
from config.settings import settings

settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = settings.LOG_DIR / "rifki.log"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # zaten yapılandırılmış

    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger