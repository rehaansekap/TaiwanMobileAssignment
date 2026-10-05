"""
actions/base.py
Abstract base class untuk semua action strategy.

Setiap action baru cukup:
1. Buat class baru yang inherit BaseAction
2. Implementasikan property `name` dan method `execute()`
3. Register ke ActionRegistry di main.py

Tidak perlu ubah core logic apapun (Open/Closed Principle).
"""

from abc import ABC, abstractmethod
from models.task import Task


class BaseAction(ABC):
    """
    Strategy interface untuk semua action yang dapat dieksekusi.

    Subclass wajib mengimplementasikan:
    - `name`    : string identifier unik (e.g. 'sync', 'backup')
    - `execute` : logika eksekusi utama
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Identifier unik action ini.
        Digunakan sebagai key di ActionRegistry.
        Contoh: 'sync', 'backup', 'delete'
        """
        ...

    @abstractmethod
    def execute(self, task: Task) -> None:
        """
        Jalankan action untuk task yang diberikan.

        Args:
            task: Task object yang berisi username, params, dan metadata.

        Raises:
            Exception: Apapun yang di-raise akan ditangkap oleh TaskExecutor
                       dan menandai task sebagai FAILED.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
