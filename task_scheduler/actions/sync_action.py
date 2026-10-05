"""
actions/sync_action.py
Implementasi action untuk sinkronisasi data/direktori.

Params yang didukung (via task.params):
    target (str)      : Path atau endpoint yang akan di-sync. Required.
    dry_run (bool)    : Jika True, simulasi tanpa benar-benar sync. Default False.
    retries (int)     : Jumlah percobaan ulang jika gagal. Default 1.
"""

import logging
import time
from actions.base import BaseAction
from models.task import Task

logger = logging.getLogger(__name__)


class SyncAction(BaseAction):
    """Action untuk mensinkronisasi target ke destination."""

    @property
    def name(self) -> str:
        return "sync"

    def execute(self, task: Task) -> None:
        target  = task.params.get("target")
        dry_run = task.params.get("dry_run", False)
        retries = task.params.get("retries", 1)

        if not target:
            raise ValueError("SyncAction membutuhkan parameter 'target'.")

        logger.info(
            f"[SYNC] user='{task.username}' | target='{target}' | "
            f"dry_run={dry_run} | retries={retries}"
        )

        for attempt in range(1, retries + 1):
            try:
                logger.debug(f"[SYNC] Attempt {attempt}/{retries} for '{target}'")

                if dry_run:
                    logger.info(f"[SYNC] DRY-RUN — skipping actual sync for '{target}'")
                else:
                    # ── Placeholder untuk logika sync nyata ──────────────────
                    # Contoh real: subprocess.run(['rsync', '-avz', target, dest])
                    time.sleep(0.05)  # simulasi I/O
                    logger.info(f"[SYNC] Successfully synced '{target}'")

                return  # sukses, keluar dari loop retry

            except Exception as exc:
                logger.warning(f"[SYNC] Attempt {attempt} failed: {exc}")
                if attempt == retries:
                    raise
