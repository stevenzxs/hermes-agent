"""Policy shared by schedule editing and finite manual rounds."""


def retire_exhausted(job: dict) -> None:
    from cron.jobs import _complete_job_record

    repeat = job.get("repeat") or {}
    limit = repeat.get("times")
    if limit is not None and repeat.get("completed", 0) >= limit:
        _complete_job_record(job)
