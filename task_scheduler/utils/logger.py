"""
utils/logger.py
Centralized logging setup untuk Task Scheduler.

Mendukung dual handler:
- StreamHandler  → output ke stdout (console)
- FileHandler    → output ke task_scheduler.log (audit trail)
"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "task_scheduler",
    level: int = logging.DEBUG,
    log_file: str | None = "task_scheduler.log",
) -> logging.Logger:
    """
    Inisialisasi root logger untuk task_scheduler.

    Args:
        name:     Nama logger (default: 'task_scheduler').
        level:    Log level minimum (default: DEBUG).
        log_file: Path ke file log. Set None untuk disable file logging.

    Returns:
        Logger yang sudah dikonfigurasi.
    """
    logger = logging.getLogger(name)

    # Hindari duplikat handler jika setup_logger dipanggil lebih dari sekali
    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — INFO ke atas tampil di terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler — semua level (DEBUG ke atas) masuk ke log file
    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Cegah propagasi ke root logger agar tidak double-print
    logger.propagate = False

    return logger
