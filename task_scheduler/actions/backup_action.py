"""
actions/backup_action.py
Implementasi action untuk backup data/direktori.

Params yang didukung (via task.params):
    target      (str)  : Path sumber yang akan di-backup. Required.
    destination (str)  : Path tujuan backup. Default '/backup/default'.
    compress    (bool) : Jika True, kompres hasil backup. Default True.
"""

import logging
import time
from actions.base import BaseAction
from models.task import Task

logger = logging.getLogger(__name__)


class BackupAction(BaseAction):
    """Action untuk membuat backup dari source ke destination."""

    @property
    def name(self) -> str:
        return "backup"

    def execute(self, task: Task) -> None:
        target      = task.params.get("target")
        destination = task.params.get("destination", "/backup/default")
        compress    = task.params.get("compress", True)

        if not target:
            raise ValueError("BackupAction membutuhkan parameter 'target'.")

        logger.info(
            f"[BACKUP] user='{task.username}' | source='{target}' | "
            f"dest='{destination}' | compress={compress}"
        )

        # ── Placeholder untuk logika backup nyata ──────────────────────────
        # Contoh real: shutil.make_archive(destination, 'gztar', target)
        time.sleep(0.05)  # simulasi I/O
        compression_label = "compressed" if compress else "uncompressed"
        logger.info(
            f"[BACKUP] Successfully backed up '{target}' → "
            f"'{destination}' ({compression_label})"
        )
