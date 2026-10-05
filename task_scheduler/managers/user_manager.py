"""
managers/user_manager.py
User management & quota control module.

Bertanggung jawab atas:
- Register / unregister user
- Lookup user by username
- Quota enforcement (consume & reset)
- Listing semua user
"""

import logging
from models.user import User
from utils.exceptions import UserNotFoundError, UserAlreadyExistsError

logger = logging.getLogger(__name__)


class UserManager:
    """
    Manager terpusat untuk semua operasi user dan quota.

    Menyimpan user di in-memory dict. Untuk persistensi jangka panjang,
    inject storage adapter ke constructor (future extension).
    """

    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, username: str, quota: int) -> User:
        """
        Daftarkan user baru dengan quota tertentu.

        Args:
            username: Identifier unik user.
            quota:    Batas maksimum task yang boleh dieksekusi.

        Returns:
            User object yang baru dibuat.

        Raises:
            UserAlreadyExistsError: Jika username sudah terdaftar.
            ValueError: Jika quota <= 0.
        """
        if quota <= 0:
            raise ValueError(f"Quota harus > 0, didapat: {quota}")
        if username in self._users:
            raise UserAlreadyExistsError(username)

        user = User(username=username, quota=quota)
        self._users[username] = user
        logger.info(f"User registered: {user}")
        return user

    def unregister(self, username: str) -> None:
        """
        Hapus user dari manager.

        Raises:
            UserNotFoundError: Jika username tidak ditemukan.
        """
        self._get_or_raise(username)
        del self._users[username]
        logger.info(f"User unregistered: '{username}'")

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, username: str) -> User:
        """
        Ambil User object berdasarkan username.

        Raises:
            UserNotFoundError: Jika username tidak ditemukan.
        """
        return self._get_or_raise(username)

    def exists(self, username: str) -> bool:
        """Return True jika username terdaftar."""
        return username in self._users

    def all_users(self) -> list[User]:
        """Return list semua User yang terdaftar."""
        return list(self._users.values())

    # ── Quota Operations ──────────────────────────────────────────────────────

    def consume_quota(self, username: str) -> None:
        """
        Validasi user ada & kurangi quota satu unit.

        Raises:
            UserNotFoundError:  Jika user tidak ditemukan.
            QuotaExceededError: Jika quota sudah habis (dilempar dari User).
        """
        user = self._get_or_raise(username)
        user.consume_quota()
        logger.debug(
            f"Quota consumed for '{username}': "
            f"{user.executed}/{user.quota} used, {user.remaining_quota} remaining"
        )

    def reset_quota(self, username: str) -> None:
        """Reset quota satu user tertentu."""
        user = self._get_or_raise(username)
        user.reset_quota()
        logger.info(f"Quota reset for user '{username}'")

    def reset_all_quotas(self) -> None:
        """Reset quota semua user (e.g., dipanggil setiap hari baru)."""
        for user in self._users.values():
            user.reset_quota()
        logger.info(f"Quota reset for all {len(self._users)} users.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, username: str) -> User:
        if username not in self._users:
            raise UserNotFoundError(username)
        return self._users[username]

    def __repr__(self) -> str:
        return f"UserManager(users={list(self._users.keys())})"
