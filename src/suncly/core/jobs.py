"""The worker loop: claim, lease, heartbeat, execute, finish, recover.

Stateless workers pull from the Postgres-backed job table (schema §2, §7).
A handler runs one job while a heartbeat thread extends the lease; if the
lease cannot be extended (the reaper took it, or the job was cancelled) the
handler learns it through ``JobContext`` and stops. Every outcome is written
back through ``finish_attempt``; an exception is a failed attempt, retried
with exponential backoff up to the job's ``max_attempts``.
"""

from __future__ import annotations

import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Protocol

from suncly.core.app_config import WorkerConfig
from suncly.domain.errors import JobError
from suncly.domain.jobs import AttemptOutcome, ExecutionAttempt, Job, JobKind, backoff_seconds
from suncly.domain.models import JsonObject
from suncly.ports.app_store import ApplicationStore
from suncly.ports.clock import Clock


class JobCancelledError(Exception):
    """Raised by a handler when it stopped because cancellation was requested."""


class LeaseLostError(Exception):
    """Raised when the worker's lease on the job is gone; the attempt is not finished by us."""


@dataclass
class JobContext:
    """What a handler may do while it runs: heartbeat, persist progress, learn of cancellation."""

    job: Job
    attempt: ExecutionAttempt
    store: ApplicationStore
    clock: Clock
    lease_seconds: float
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _cancel_requested: bool = False
    _lease_lost: bool = False
    _progress: JsonObject = field(default_factory=dict)

    @property
    def cancel_requested(self) -> bool:
        with self._lock:
            return self._cancel_requested

    @property
    def lease_lost(self) -> bool:
        with self._lock:
            return self._lease_lost

    def heartbeat(self) -> None:
        job = self.store.heartbeat(
            self.job.id, self.attempt.id, self.clock.now(), self.lease_seconds
        )
        with self._lock:
            if job is None:
                self._lease_lost = True
            else:
                self._cancel_requested = job.cancel_requested

    def check(self) -> None:
        """Raise when the handler must stop."""
        if self.lease_lost:
            raise LeaseLostError(f"lease on job {self.job.id} was lost")

    def update_progress(self, **changes: object) -> JsonObject:
        with self._lock:
            self._progress.update(changes)
            snapshot = dict(self._progress)
        self.store.update_progress(self.job.id, snapshot)
        return snapshot

    def progress(self) -> JsonObject:
        with self._lock:
            return dict(self._progress)


class JobHandler(Protocol):
    kind: JobKind

    def handle(self, context: JobContext) -> None:
        """Do the work. Return on success; raise ``JobCancelledError`` or any error otherwise."""
        ...


class WorkerLoop:
    def __init__(
        self,
        store: ApplicationStore,
        clock: Clock,
        config: WorkerConfig,
        handlers: list[JobHandler],
        worker_id: str,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._config = config
        self._handlers = {handler.kind: handler for handler in handlers}
        self._worker_id = worker_id
        self._log = on_log or (lambda line: None)

    @property
    def kinds(self) -> list[JobKind]:
        return list(self._handlers)

    def recover(self) -> list[Job]:
        recovered = self._store.recover_expired_leases(self._clock.now())
        for job in recovered:
            self._log(f"recovered job {job.id}: lease expired, now {job.status.value}")
        return recovered

    def run_once(self) -> bool:
        """Recover expired leases, then claim and run one job. Returns whether one ran."""
        self.recover()
        claimed = self._store.claim_job(
            self._worker_id, self._clock.now(), self._config.lease_seconds, self.kinds
        )
        if claimed is None:
            return False
        job, attempt = claimed
        self._log(f"claimed job {job.id} ({job.kind.value}) attempt {attempt.number}")
        context = JobContext(job, attempt, self._store, self._clock, self._config.lease_seconds)
        context._progress = dict(job.progress)
        stop = threading.Event()
        beater = threading.Thread(
            target=self._beat, args=(context, stop), name=f"heartbeat-{job.id}", daemon=True
        )
        beater.start()
        try:
            self._handlers[job.kind].handle(context)
        except JobCancelledError:
            self._finish(context, AttemptOutcome.CANCELLED, None)
        except LeaseLostError as exc:
            self._log(f"job {job.id}: {exc}; leaving it to the reaper")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._log(f"job {job.id} failed: {error}\n{traceback.format_exc()}")
            self._finish(context, AttemptOutcome.FAILED, error)
        else:
            self._finish(context, AttemptOutcome.SUCCEEDED, None)
        finally:
            stop.set()
            beater.join(timeout=5)
        return True

    def _finish(self, context: JobContext, outcome: AttemptOutcome, error: str | None) -> None:
        now = self._clock.now()
        run_after = None
        if outcome is AttemptOutcome.FAILED:
            run_after = now + timedelta(
                seconds=backoff_seconds(
                    context.job.attempts,
                    self._config.retry_base_seconds,
                    self._config.retry_cap_seconds,
                )
            )
        try:
            job = self._store.finish_attempt(
                context.job.id, context.attempt.id, outcome, now, error, run_after
            )
        except JobError as exc:
            self._log(f"job {context.job.id}: could not finish attempt: {exc}")
            return
        self._log(
            f"job {job.id}: attempt {context.attempt.number} {outcome.value}; "
            f"job {job.status.value}"
        )

    def _beat(self, context: JobContext, stop: threading.Event) -> None:
        while not stop.wait(self._config.heartbeat_seconds):
            try:
                context.heartbeat()
            except Exception as exc:  # a failing heartbeat is a lost lease, never a crash
                self._log(f"heartbeat failed: {exc}")
                with context._lock:
                    context._lease_lost = True
            if context.lease_lost:
                return

    def run_forever(self, stop: threading.Event) -> None:
        while not stop.is_set():
            ran = self.run_once()
            if not ran:
                stop.wait(self._config.poll_seconds)
