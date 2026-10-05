# Refactor Plan: Task Scheduler System

## 📌 Analisis Kode Saat Ini

| Masalah | Dampak |
|---|---|
| Data `users` & `tasks` adalah global dict/list | Tidak ada encapsulation, rentan mutasi tak terduga |
| Logika quota check inline di `run()` | Sulit di-extend atau di-test secara terisolasi |
| `action` hanya string tanpa abstraksi | Menambah action baru = mengubah core logic |
| Tidak ada logging | Sulit debug & audit |
| Tidak ada error handling | Crash saat user tidak ditemukan, format waktu salah, dsb |
| Scheduling hanya pakai `strftime` manual | Tidak scalable, tidak bisa run berulang |

---

## 🏗️ Arsitektur Target

```
task_scheduler/
│
├── main.py                    # Entry point
│
├── models/
│   ├── __init__.py
│   ├── user.py                # User dataclass + quota logic
│   └── task.py                # Task dataclass + status tracking
│
├── actions/
│   ├── __init__.py
│   ├── base.py                # Abstract base class Action
│   ├── sync_action.py         # SyncAction
│   ├── backup_action.py       # BackupAction
│   └── delete_action.py       # DeleteAction
│
├── managers/
│   ├── __init__.py
│   ├── user_manager.py        # CRUD user + quota enforcement
│   └── task_manager.py        # Register, queue, track tasks
│
├── scheduler/
│   ├── __init__.py
│   └── scheduler.py           # Scheduling loop (sync / async)
│
└── utils/
    ├── __init__.py
    └── logger.py              # Centralized logging setup
```

---

## 🔷 Module & Logic Design

### 1. `models/user.py` — User Data Model

```python
from dataclasses import dataclass, field

@dataclass
class User:
    username: str
    quota: int
    executed: int = 0

    @property
    def remaining_quota(self) -> int:
        return self.quota - self.executed

    def has_quota(self) -> bool:
        return self.executed < self.quota

    def consume_quota(self) -> None:
        if not self.has_quota():
            raise QuotaExceededError(f"User '{self.username}' has exceeded quota.")
        self.executed += 1

    def reset_quota(self) -> None:
        self.executed = 0
```

> **Saran**: Gunakan `@dataclass` agar immutable-friendly dan mudah di-serialize ke JSON/DB. `QuotaExceededError` adalah custom exception, lihat bagian Error Handling.

---

### 2. `models/task.py` — Task Data Model

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class TaskStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    SKIPPED   = "skipped"   # quota exceeded / user not found

@dataclass
class Task:
    task_id: str              # UUID atau incremental ID
    username: str
    action: str               # key untuk ActionRegistry
    scheduled_time: str       # format "HH:MM"
    params: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    error_message: str | None = None
```

> **Saran**: `params` sebagai `dict` membuat task fully configurable tanpa ubah model — `{'target': '/data/x', 'compress': True, 'retries': 3}`.

---

### 3. `actions/base.py` — Strategy Pattern untuk Action

```python
from abc import ABC, abstractmethod
from models.task import Task

class BaseAction(ABC):
    """Abstract base class untuk semua action."""

    @abstractmethod
    def execute(self, task: Task) -> None:
        """Jalankan action. Raise exception jika gagal."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier unik action ini (e.g. 'sync', 'backup')."""
        ...
```

**Contoh implementasi:**

```python
# actions/sync_action.py
import logging
from actions.base import BaseAction
from models.task import Task

logger = logging.getLogger(__name__)

class SyncAction(BaseAction):
    name = "sync"

    def execute(self, task: Task) -> None:
        target = task.params.get("target", "unknown")
        logger.info(f"[SYNC] Syncing target='{target}' for user='{task.username}'")
        # ... real sync logic ...
```

> **Saran**: Action baru cukup buat file baru + register ke `ActionRegistry`. Zero change ke core logic — ini adalah prinsip **Open/Closed Principle (OCP)**.

---

### 4. `managers/user_manager.py` — User Management & Quota Control

```python
class UserManager:
    def __init__(self):
        self._users: dict[str, User] = {}

    def register(self, username: str, quota: int) -> User:
        if username in self._users:
            raise UserAlreadyExistsError(username)
        user = User(username=username, quota=quota)
        self._users[username] = user
        return user

    def get(self, username: str) -> User:
        if username not in self._users:
            raise UserNotFoundError(username)
        return self._users[username]

    def consume_quota(self, username: str) -> None:
        """Validate + consume. Raise jika user tidak ada atau quota habis."""
        user = self.get(username)
        user.consume_quota()  # raise QuotaExceededError internally

    def reset_all_quotas(self) -> None:
        for user in self._users.values():
            user.reset_quota()
```

---

### 5. `managers/task_manager.py` — Task Registry & Executor

```python
class ActionRegistry:
    """Map action name → BaseAction instance."""
    _registry: dict[str, BaseAction] = {}

    @classmethod
    def register(cls, action: BaseAction) -> None:
        cls._registry[action.name] = action

    @classmethod
    def get(cls, name: str) -> BaseAction:
        if name not in cls._registry:
            raise UnknownActionError(name)
        return cls._registry[name]


class TaskExecutor:
    def __init__(self, user_manager: UserManager):
        self._user_manager = user_manager
        self._logger = logging.getLogger(__name__)

    def execute(self, task: Task) -> None:
        task.status = TaskStatus.RUNNING
        try:
            self._user_manager.consume_quota(task.username)
            action = ActionRegistry.get(task.action)
            action.execute(task)
            task.status = TaskStatus.DONE
            self._logger.info(f"Task '{task.task_id}' DONE.")
        except QuotaExceededError as e:
            task.status = TaskStatus.SKIPPED
            self._logger.warning(str(e))
        except UserNotFoundError as e:
            task.status = TaskStatus.SKIPPED
            self._logger.error(str(e))
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            self._logger.exception(f"Task '{task.task_id}' FAILED: {e}")
```

---

### 6. `scheduler/scheduler.py` — Scheduling System

```python
import time
import datetime
import threading

class Scheduler:
    def __init__(self, executor: TaskExecutor, poll_interval: int = 30):
        self._tasks: list[Task] = []
        self._executor = executor
        self._poll_interval = poll_interval  # seconds

    def add_task(self, task: Task) -> None:
        self._tasks.append(task)

    def _get_due_tasks(self) -> list[Task]:
        now = datetime.datetime.now().strftime('%H:%M')
        return [
            t for t in self._tasks
            if t.scheduled_time == now and t.status == TaskStatus.PENDING
        ]

    def run_once(self) -> None:
        """Jalankan semua task yang due sekarang."""
        for task in self._get_due_tasks():
            self._executor.execute(task)

    def run_loop(self) -> None:
        """Blocking loop — cocok untuk simple daemon."""
        while True:
            self.run_once()
            time.sleep(self._poll_interval)

    def run_threaded(self) -> threading.Thread:
        """Non-blocking — jalankan scheduler di background thread."""
        t = threading.Thread(target=self.run_loop, daemon=True)
        t.start()
        return t
```

> **Optional async version** menggunakan `asyncio` bisa dicapai dengan mengganti `time.sleep` → `await asyncio.sleep` dan `execute` → `await executor.execute(task)` dengan `async def`.

---

## 🚨 Error Handling & Logging

### Custom Exception Hierarchy

```
TaskSchedulerError (base)
├── UserNotFoundError
├── UserAlreadyExistsError
├── QuotaExceededError
└── UnknownActionError
```

Semua custom exception mewarisi dari satu base — memudahkan `except TaskSchedulerError` untuk global handler.

### Logging Strategy

```python
# utils/logger.py
import logging
import sys

def setup_logger(name: str = "task_scheduler", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)

    # File handler (audit trail)
    fh = logging.FileHandler("task_scheduler.log")
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger
```

**Prinsip logging per layer:**

| Layer | Log Level | Contoh |
|---|---|---|
| Scheduler | `DEBUG` | "Checking due tasks at 12:00" |
| TaskExecutor | `INFO` | "Task 'abc123' DONE" |
| UserManager | `WARNING` | "Quota exceeded for alice" |
| Action | `INFO` | "[SYNC] Syncing /data/x" |
| Exception catch-all | `ERROR` / `EXCEPTION` | Full traceback |

---

## 🔧 Maintainability Jangka Panjang

### 1. Dependency Injection (DI)
`TaskExecutor` menerima `UserManager` lewat constructor — bukan hard-coded. Memudahkan **unit testing** dengan mock object.

```python
# Test example
mock_user_manager = Mock(spec=UserManager)
executor = TaskExecutor(user_manager=mock_user_manager)
```

### 2. Configuration via File/Dict
Hindari hardcode user & task. Gunakan config loader:

```python
# config.yaml
users:
  - username: alice
    quota: 3
  - username: bob
    quota: 5

tasks:
  - user: alice
    time: "12:00"
    action: sync
    params:
      target: /data/x
```

### 3. Task Persistence (Future-proofing)
Desain `Task` sebagai dataclass memudahkan serialisasi:
- `dataclasses.asdict(task)` → JSON → simpan ke file/DB
- Bisa di-reload setelah restart tanpa kehilangan state

### 4. Open for Extension, Closed for Modification
- Action baru → buat class baru, register ke `ActionRegistry`
- Scheduler baru (cron-based, async) → implement interface baru
- Storage backend baru → inject storage adapter ke `UserManager`

---

## 🗺️ Phased Implementation Roadmap

```
Phase 1 (Core)          Phase 2 (Robustness)      Phase 3 (Optional)
─────────────────       ─────────────────────      ─────────────────
models/user.py    →     Error hierarchy       →    async scheduler
models/task.py    →     logging setup         →    config file loader
actions/base.py   →     unit tests            →    task persistence
user_manager.py   →     quota reset logic     →    REST API endpoint
task_executor.py  →     
scheduler.py      →     
main.py           →     
```

---

## ✅ Summary: Keputusan Desain Kunci

| Keputusan | Alasan |
|---|---|
| `@dataclass` untuk model | Boilerplate minimal, mudah serialize |
| Strategy Pattern untuk Action | OCP — tambah action tanpa ubah core |
| DI untuk `UserManager` | Testability & loose coupling |
| Custom exception hierarchy | Granular error handling, satu base untuk global catch |
| `logging` module (bukan `print`) | Audit trail, configurable level, file output |
| `ActionRegistry` sebagai class dict | Decoupled registration, self-documenting |
| `TaskStatus` enum | Explicit state machine, hindari magic string |
