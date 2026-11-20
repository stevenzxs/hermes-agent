"""Explicit, history-preserving successors; no scheduler side effects."""

import copy
import re
import uuid


def open_round(job_id: str, request_id: str) -> dict:
    from cron import jobs
    from cron.job_definition import JOB_DEFINITION_FIELDS

    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id):
        raise ValueError("A valid request_id (8–128 characters) is required")
    with jobs._jobs_lock():
        records = jobs.load_jobs()
        existing = next((j for j in records if j.get("round_parent_id") == job_id
                         and j.get("round_request_id") == request_id), None)
        if existing is not None:
            return copy.deepcopy(existing)
        original = next((j for j in records if j["id"] == job_id), None)
        if original is None:
            raise ValueError("Original job not found")
        if not jobs.is_terminal_job(original):
            raise ValueError("Only a terminal job can open a new round")
        new = {k: copy.deepcopy(v) for k, v in original.items() if k in JOB_DEFINITION_FIELDS}
        new.update(
            id=uuid.uuid4().hex[:12], round_parent_id=job_id, round_request_id=request_id,
            repeat={"times": (original.get("repeat") or {}).get("times"), "completed": 0},
            enabled=False, state="paused", next_run_at=None,
            created_at=jobs._hermes_now().isoformat(), paused_at=jobs._hermes_now().isoformat(),
            paused_reason="New round; explicitly enable or trigger when ready.",
            last_run_at=None, last_status=None, last_error=None,
        )
        jobs.save_jobs(records + [new])
        return copy.deepcopy(new)
