"""Request-scoped diagnostics emitted at the locked fire admission boundary."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


MESSAGES = {
    "manual_only": "This job only accepts explicit manual triggers.",
    "claim_conflict": "Execution was not acquired; check the job's run history before retrying.",
    "execution_limit_reached": "This job has reached its execution limit. Open a new round to run it again.",
    "job_completed": "This job is completed. Open a new round to run it again.",
    "job_terminal": "This job is in a terminal state and cannot be triggered.",
    "job_paused": "This job is paused or disabled.",
    "job_running": "This job already has an active execution claim.",
    "occurrence_completed": "This scheduled occurrence has already completed.",
}


@dataclass
class FireRefusal:
    code: str = "claim_conflict"

    @property
    def message(self) -> str:
        return MESSAGES[self.code]


_current: ContextVar[FireRefusal | None] = ContextVar("cron_fire_refusal", default=None)


@contextmanager
def capture_refusal():
    """Capture only this call's admission decision, restoring any outer request."""
    refusal = FireRefusal()
    token = _current.set(refusal)
    try:
        yield refusal
    finally:
        _current.reset(token)


def refuse(code: str) -> bool:
    """Keep the legacy False result while attaching an authoritative reason."""
    if (refusal := _current.get()) is not None:
        refusal.code = code
    return False


def refuse_terminal(job: dict) -> bool:
    repeat = job.get("repeat") or {}
    limit = repeat.get("times")
    if limit is not None and repeat.get("completed", 0) >= limit:
        return refuse("execution_limit_reached")
    return refuse("job_completed" if job.get("state") == "completed" else "job_terminal")
