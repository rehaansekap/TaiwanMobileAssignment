"""
scheduler/scheduler.py
Scheduling system — polling-based, mendukung 3 mode eksekusi.

Mode:
    run_once()    → Jalankan sekali (cocok untuk testing / one-shot cron).
    run_loop()    → Blocking loop polling (cocok untuk daemon/service).
    run_threaded()→ Non-blocking di background thread (embed ke app lain).
"""

import datetime
import logging
import threading
import time
from models.task import Task, TaskStatus
from managers.task_manager import TaskExecutor

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Polling-based task scheduler.

    Setiap `poll_interval` detik, scheduler memeriksa task mana yang
    jadwal eksekusinya cocok dengan waktu sekarang, lalu mengeksekusinya
    via TaskExecutor.

    Satu user bisa punya multiple task — scheduler menjalankan semua
    task PENDING yang due secara berurutan dalam satu poll cycle.
    """

    def __init__(
        self,
        executor: TaskExecutor,
        poll_interval: int = 30,
    ) -> None:
        """
        Args:
            executor:      TaskExecutor yang akan menjalankan setiap task.
            poll_interval: Interval polling dalam detik (default 30s).
        """
        self._tasks: list[Task] = []
        self._executor = executor
        self._poll_interval = poll_interval
        self._lock = threading.Lock()  # thread-safe task list access

    # ── Task Registration ──────────────────────────────────────────────────────

    def add_task(self, task: Task) -> None:
        """Tambahkan task ke scheduler queue."""
        with self._lock:
            self._tasks.append(task)
        logger.debug(
            f"Task added to scheduler | id={task.task_id[:8]}... | "
            f"user='{task.username}' | action='{task.action}' | "
            f"scheduled_time='{task.scheduled_time}'"
        )

    def remove_task(self, task_id: str) -> bool:
        """
        Hapus task dari scheduler berdasarkan task_id.

        Returns:
            True jika task ditemukan dan dihapus, False jika tidak ada.
        """
        with self._lock:
            before = len(self._tasks)
            self._tasks = [t for t in self._tasks if t.task_id != task_id]
            removed = len(self._tasks) < before
        if removed:
            logger.debug(f"Task removed from scheduler | id={task_id[:8]}...")
        return removed

    def pending_tasks(self) -> list[Task]:
        """Return list semua task yang masih berstatus PENDING."""
        with self._lock:
            return [t for t in self._tasks if t.is_pending()]

    # ── Core Scheduling Logic ─────────────────────────────────────────────────

    def _get_due_tasks(self) -> list[Task]:
        """
        Return semua task PENDING yang scheduled_time-nya cocok
        dengan waktu sekarang (format HH:MM).
        """
        now = datetime.datetime.now().strftime("%H:%M")
        with self._lock:
            due = [
                t for t in self._tasks
                if t.scheduled_time == now and t.is_pending()
            ]
        logger.debug(f"Poll at {now} — {len(due)} task(s) due")
        return due

    # ── Execution Modes ───────────────────────────────────────────────────────

    def run_once(self) -> list[Task]:
        """
        Periksa & jalankan semua task yang due sekarang (satu kali).

        Returns:
            List task yang diproses dalam cycle ini.
        """
        due_tasks = self._get_due_tasks()
        for task in due_tasks:
            self._executor.execute(task)
        return due_tasks

    def run_loop(self, stop_event: threading.Event | None = None) -> None:
        """
        Blocking loop — polling setiap `poll_interval` detik.

        Args:
            stop_event: threading.Event untuk menghentikan loop secara graceful.
                        Jika None, loop berjalan sampai KeyboardInterrupt / kill.
        """
        logger.info(
            f"Scheduler loop started | poll_interval={self._poll_interval}s"
        )
        try:
            while True:
                if stop_event and stop_event.is_set():
                    logger.info("Scheduler loop stopped via stop_event.")
                    break
                self.run_once()
                time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            logger.info("Scheduler loop interrupted by user (KeyboardInterrupt).")

    def run_threaded(self) -> tuple[threading.Thread, threading.Event]:
        """
        Jalankan scheduler di background daemon thread (non-blocking).

        Returns:
            Tuple (thread, stop_event).
            Panggil stop_event.set() untuk menghentikan scheduler secara graceful.

        Example:
            thread, stop = scheduler.run_threaded()
            # ... kode lain ...
            stop.set()
            thread.join()
        """
        stop_event = threading.Event()
        thread = threading.Thread(
            target=self.run_loop,
            args=(stop_event,),
            daemon=True,
            name="SchedulerThread",
        )
        thread.start()
        logger.info("Scheduler running in background thread.")
        return thread, stop_event

    # ── Summary ───────────────────────────────────────────────────────────────

    def status_summary(self) -> dict:
        """Return ringkasan status semua task untuk monitoring."""
        with self._lock:
            tasks = list(self._tasks)
        summary: dict[str, int] = {}
        for task in tasks:
            key = task.status.value
            summary[key] = summary.get(key, 0) + 1
        return {"total": len(tasks), "by_status": summary}

    def __repr__(self) -> str:
        return (
            f"Scheduler(tasks={len(self._tasks)}, "
            f"poll_interval={self._poll_interval}s)"
        )
