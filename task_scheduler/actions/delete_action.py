"""
actions/delete_action.py
Implementasi action untuk menghapus file/direktori.

Params yang didukung (via task.params):
    target      (str)  : Path yang akan dihapus. Required.
    safe_delete (bool) : Jika True, pindah ke trash alih-alih hapus permanen. Default True.
"""

import logging
import time
from actions.base import BaseAction
from models.task import Task

logger = logging.getLogger(__name__)


class DeleteAction(BaseAction):
    """Action untuk menghapus file atau direktori target."""

    @property
    def name(self) -> str:
        return "delete"

    def execute(self, task: Task) -> None:
        target      = task.params.get("target")
        safe_delete = task.params.get("safe_delete", True)

        if not target:
            raise ValueError("DeleteAction membutuhkan parameter 'target'.")

        mode = "safe (move to trash)" if safe_delete else "permanent"
        logger.info(
            f"[DELETE] user='{task.username}' | target='{target}' | mode={mode}"
        )

        # ── Placeholder untuk logika delete nyata ─────────────────────────
        # Contoh real safe: send2trash.send2trash(target)
        # Contoh real perm: shutil.rmtree(target) atau os.remove(target)
        time.sleep(0.05)  # simulasi I/O
        logger.info(f"[DELETE] Successfully deleted '{target}' ({mode})")
