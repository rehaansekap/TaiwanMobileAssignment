"""
managers/task_manager.py
ActionRegistry + TaskExecutor.

ActionRegistry : Map action name → BaseAction instance (Strategy Pattern).
TaskExecutor   : Orchestrate quota check + action dispatch + status update.
"""

import logging
from models.task import Task, TaskStatus
from managers.user_manager import UserManager
from actions.base import BaseAction
from utils.exceptions import (
    QuotaExceededError,
    UserNotFoundError,
    UnknownActionError,
    TaskSchedulerError,
)

logger = logging.getLogger(__name__)


# ── Action Registry ───────────────────────────────────────────────────────────

class ActionRegistry:
    """
    Registry terpusat yang memetakan nama action ke instans BaseAction.

    Cara menambah action baru:
        ActionRegistry.register(MyNewAction())
    Tidak perlu modifikasi di tempat lain (Open/Closed Principle).
    """

    _registry: dict[str, BaseAction] = {}

    @classmethod
    def register(cls, action: BaseAction) -> None:
        """
        Daftarkan action ke registry.

        Args:
            action: Instans yang mengimplementasikan BaseAction.

        Raises:
            TypeError: Jika action bukan subclass BaseAction.
        """
        if not isinstance(action, BaseAction):
            raise TypeError(
                f"Action harus merupakan subclass BaseAction, "
                f"didapat: {type(action).__name__}"
            )
        cls._registry[action.name] = action
        logger.debug(f"Action registered: '{action.name}' → {action!r}")

    @classmethod
    def get(cls, name: str) -> BaseAction:
        """
        Ambil action berdasarkan nama.

        Raises:
            UnknownActionError: Jika nama tidak terdaftar.
        """
        if name not in cls._registry:
            raise UnknownActionError(name)
        return cls._registry[name]

    @classmethod
    def available_actions(cls) -> list[str]:
        """Return list nama semua action yang terdaftar."""
        return list(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear semua action dari registry (terutama untuk testing)."""
        cls._registry.clear()


# ── Task Executor ─────────────────────────────────────────────────────────────

class TaskExecutor:
    """
    Mengeksekusi satu Task dengan urutan:
    1. Set status → RUNNING
    2. Consume quota user
    3. Dispatch ke action yang sesuai
    4. Update status → DONE / FAILED / SKIPPED

    Menerima UserManager via constructor (Dependency Injection)
    sehingga mudah di-mock saat unit testing.
    """

    def __init__(self, user_manager: UserManager) -> None:
        self._user_manager = user_manager

    def execute(self, task: Task) -> None:
        """
        Jalankan task secara synchronous.

        Status akhir task:
        - DONE    : action selesai sukses
        - SKIPPED : quota habis atau user tidak ditemukan
        - FAILED  : action melempar exception
        """
        logger.info(
            f"Executing task | id={task.task_id[:8]}... | "
            f"user='{task.username}' | action='{task.action}'"
        )
        task.mark_running()

        try:
            # ① Validasi & consume quota
            self._user_manager.consume_quota(task.username)

            # ② Ambil & jalankan action
            action = ActionRegistry.get(task.action)
            action.execute(task)

            # ③ Tandai selesai
            task.mark_done()
            logger.info(
                f"Task DONE | id={task.task_id[:8]}... | "
                f"user='{task.username}' | action='{task.action}'"
            )

        except (QuotaExceededError, UserNotFoundError) as e:
            # Task dilewati — bukan kegagalan action, tapi kondisi bisnis
            task.mark_skipped()
            logger.warning(f"Task SKIPPED | id={task.task_id[:8]}... | reason: {e}")

        except TaskSchedulerError as e:
            # Error sistem lain (e.g. UnknownActionError)
            task.mark_failed(str(e))
            logger.error(
                f"Task FAILED (scheduler error) | id={task.task_id[:8]}... | {e}"
            )

        except Exception as e:
            # Error tak terduga dari dalam action
            task.mark_failed(str(e))
            logger.exception(
                f"Task FAILED (unexpected) | id={task.task_id[:8]}... | {e}"
            )
