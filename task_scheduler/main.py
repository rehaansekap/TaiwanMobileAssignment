"""
main.py — Entry point Task Scheduler System.

Urutan inisialisasi:
    1. Setup logging
    2. Register semua action ke ActionRegistry
    3. Register users ke UserManager
    4. Definisikan tasks
    5. Tambahkan tasks ke Scheduler
    6. Jalankan scheduler (pilih mode)
"""

import logging
import sys
import uuid

# ── Internal imports (pastikan working directory = task_scheduler/) ───────────
from utils.logger import setup_logger
from models.task import Task
from managers.user_manager import UserManager
from managers.task_manager import ActionRegistry, TaskExecutor
from scheduler.scheduler import Scheduler
from actions.sync_action import SyncAction
from actions.backup_action import BackupAction
from actions.delete_action import DeleteAction
from utils.exceptions import TaskSchedulerError


# ─────────────────────────────────────────────────────────────────────────────
# 1. Setup Logging
# ─────────────────────────────────────────────────────────────────────────────
setup_logger(
    name="task_scheduler",
    level=logging.DEBUG,
    log_file="task_scheduler.log",
)
logger = logging.getLogger("task_scheduler.main")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Register Actions
# ─────────────────────────────────────────────────────────────────────────────
ActionRegistry.register(SyncAction())
ActionRegistry.register(BackupAction())
ActionRegistry.register(DeleteAction())

logger.info(
    f"Actions registered: {ActionRegistry.available_actions()}"
)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Setup User Manager
# ─────────────────────────────────────────────────────────────────────────────
user_manager = UserManager()

try:
    user_manager.register(username="alice", quota=3)
    user_manager.register(username="bob",   quota=5)
except TaskSchedulerError as e:
    logger.error(f"Failed to register user: {e}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Define Tasks
#    params adalah dict bebas — setiap action mengambil key yang ia butuhkan.
# ─────────────────────────────────────────────────────────────────────────────
import datetime
_NOW = datetime.datetime.now().strftime("%H:%M")  # untuk demo run_once()

tasks = [
    Task(
        username="alice",
        action="sync",
        scheduled_time=_NOW,      # ganti ke "12:00" untuk jadwal tetap
        params={
            "target": "/data/x",
            "dry_run": False,
            "retries": 2,
        },
    ),
    Task(
        username="bob",
        action="backup",
        scheduled_time=_NOW,
        params={
            "target": "/srv/y",
            "destination": "/backup/srv_y",
            "compress": True,
        },
    ),
    Task(
        username="alice",
        action="delete",
        scheduled_time=_NOW,
        params={
            "target": "/tmp/z",
            "safe_delete": True,
        },
    ),
    # Contoh task tambahan — alice memiliki multiple task sekaligus
    Task(
        username="alice",
        action="backup",
        scheduled_time=_NOW,
        params={
            "target": "/home/alice/docs",
            "destination": "/backup/alice_docs",
            "compress": False,
        },
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Setup Executor & Scheduler
# ─────────────────────────────────────────────────────────────────────────────
executor  = TaskExecutor(user_manager=user_manager)
scheduler = Scheduler(executor=executor, poll_interval=30)

for task in tasks:
    scheduler.add_task(task)

logger.info(f"Scheduler ready: {scheduler}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Run
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Task Scheduler started.")
    logger.info("=" * 60)

    # ── Opsi A: Run once (demo / testing) ────────────────────────────────────
    processed = scheduler.run_once()
    logger.info(f"run_once() processed {len(processed)} task(s).")

    # Print ringkasan status ke konsol
    summary = scheduler.status_summary()
    logger.info(f"Status summary: {summary}")

    # ── Opsi B: Blocking daemon loop ──────────────────────────────────────────
    # Uncomment baris berikut untuk mode daemon (Ctrl+C untuk stop):
    # scheduler.run_loop()

    # ── Opsi C: Background thread (non-blocking) ──────────────────────────────
    # thread, stop_event = scheduler.run_threaded()
    # ... kode lain berjalan di sini ...
    # stop_event.set()
    # thread.join()
