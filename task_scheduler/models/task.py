"""
models/task.py
Task data model dengan status tracking.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """State machine eksplisit untuk lifecycle sebuah task."""

    PENDING = "pending"    # Belum dijalankan
    RUNNING = "running"    # Sedang dieksekusi
    DONE    = "done"       # Selesai sukses
    FAILED  = "failed"     # Gagal karena exception di action
    SKIPPED = "skipped"    # Dilewati (quota habis / user tidak ditemukan)


@dataclass
class Task:
    """
    Representasi satu unit pekerjaan yang dijadwalkan.

    Attributes:
        task_id:        Identifier unik task (UUID).
        username:       Pemilik task — harus terdaftar di UserManager.
        action:         Nama action (key di ActionRegistry), e.g. 'sync'.
        scheduled_time: Waktu eksekusi dalam format 'HH:MM'.
        params:         Parameter bebas untuk action (configurable via dict).
        status:         Status saat ini (TaskStatus enum).
        error_message:  Pesan error jika status == FAILED.
    """

    username: str
    action: str
    scheduled_time: str
    params: dict[str, Any]       = field(default_factory=dict)
    status: TaskStatus           = field(default=TaskStatus.PENDING)
    error_message: str | None    = field(default=None)
    task_id: str                 = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_pending(self) -> bool:
        return self.status == TaskStatus.PENDING

    def is_done(self) -> bool:
        return self.status == TaskStatus.DONE

    def is_failed(self) -> bool:
        return self.status == TaskStatus.FAILED

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING

    def mark_done(self) -> None:
        self.status = TaskStatus.DONE
        self.error_message = None

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error_message = error

    def mark_skipped(self) -> None:
        self.status = TaskStatus.SKIPPED

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize task ke dictionary (untuk logging / persistence)."""
        return {
            "task_id": self.task_id,
            "username": self.username,
            "action": self.action,
            "scheduled_time": self.scheduled_time,
            "params": self.params,
            "status": self.status.value,
            "error_message": self.error_message,
        }

    def __repr__(self) -> str:
        return (
            f"Task(id={self.task_id[:8]}..., user={self.username!r}, "
            f"action={self.action!r}, time={self.scheduled_time!r}, "
            f"status={self.status.value})"
        )
