"""
models/user.py
User data model dengan quota control logic.
"""

from dataclasses import dataclass, field
from utils.exceptions import QuotaExceededError


@dataclass
class User:
    """
    Representasi seorang user beserta quota eksekusi task-nya.

    Attributes:
        username: Identifier unik user.
        quota:    Jumlah maksimum task yang boleh dieksekusi.
        executed: Jumlah task yang sudah dieksekusi (default 0).
    """

    username: str
    quota: int
    executed: int = field(default=0)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def remaining_quota(self) -> int:
        """Sisa quota yang masih tersedia."""
        return self.quota - self.executed

    def has_quota(self) -> bool:
        """Return True jika user masih memiliki sisa quota."""
        return self.executed < self.quota

    # ── Quota Operations ──────────────────────────────────────────────────────

    def consume_quota(self) -> None:
        """
        Kurangi satu quota dari user.

        Raises:
            QuotaExceededError: Jika quota sudah habis.
        """
        if not self.has_quota():
            raise QuotaExceededError(
                username=self.username,
                quota=self.quota,
            )
        self.executed += 1

    def reset_quota(self) -> None:
        """Reset counter executed kembali ke 0 (untuk siklus baru)."""
        self.executed = 0

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize user ke dictionary."""
        return {
            "username": self.username,
            "quota": self.quota,
            "executed": self.executed,
            "remaining_quota": self.remaining_quota,
        }

    def __repr__(self) -> str:
        return (
            f"User(username={self.username!r}, "
            f"quota={self.quota}, executed={self.executed})"
        )
