"""
utils/exceptions.py
Custom exception hierarchy untuk Task Scheduler.

TaskSchedulerError (base)
├── UserNotFoundError
├── UserAlreadyExistsError
├── QuotaExceededError
└── UnknownActionError
"""


class TaskSchedulerError(Exception):
    """Base exception untuk semua error di task scheduler."""
    pass


class UserNotFoundError(TaskSchedulerError):
    """Raise ketika username tidak ditemukan di UserManager."""
    def __init__(self, username: str) -> None:
        super().__init__(f"User '{username}' not found.")
        self.username = username


class UserAlreadyExistsError(TaskSchedulerError):
    """Raise ketika mencoba register username yang sudah ada."""
    def __init__(self, username: str) -> None:
        super().__init__(f"User '{username}' already exists.")
        self.username = username


class QuotaExceededError(TaskSchedulerError):
    """Raise ketika user sudah mencapai batas quota eksekusi."""
    def __init__(self, username: str, quota: int) -> None:
        super().__init__(
            f"User '{username}' has exceeded quota limit of {quota}."
        )
        self.username = username
        self.quota = quota


class UnknownActionError(TaskSchedulerError):
    """Raise ketika action name tidak terdaftar di ActionRegistry."""
    def __init__(self, action_name: str) -> None:
        super().__init__(
            f"Action '{action_name}' is not registered in ActionRegistry."
        )
        self.action_name = action_name
