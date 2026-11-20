"""Manual schedules never become due and each accepted run spends the finite budget."""

def test_manual_schedule_never_due_but_explicit_fire_counts(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual", repeat=2)
    assert job["schedule"]["kind"] == "manual"
    assert job["next_run_at"] is None
    assert jobs.get_due_jobs() == []
    assert jobs.claim_job_for_fire(job["id"]) is False
    for count in (1, 2):
        assert jobs.claim_job_for_fire(job["id"], manual=True) is True
        jobs.mark_job_run(job["id"], "ok")
        saved = jobs.get_job(job["id"])
        assert saved["repeat"]["completed"] == count
        assert saved["next_run_at"] is None
    assert saved["state"] == "completed"
    assert jobs.claim_job_for_fire(job["id"], manual=True, force=True) is False


def test_schedule_edit_preserves_terminal_and_consumed_budget(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual", repeat=1)
    assert jobs.claim_job_for_fire(job["id"], manual=True)
    jobs.mark_job_run(job["id"], "ok")
    edited = jobs.update_job(job["id"], {"schedule": "every 2h", "repeat": 3})
    assert edited["state"] == "completed"
    assert edited["enabled"] is False
    assert edited["next_run_at"] is None
    assert edited["repeat"] == {"times": 3, "completed": 1}


def test_paused_schedule_edit_never_enables_or_dispatches(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="every 1h", paused=True)
    edited = jobs.update_job(job["id"], {"schedule": "manual", "repeat": 1})
    assert edited["state"] == "paused"
    assert edited["enabled"] is False
    assert jobs.get_due_jobs() == []


def test_manual_schedule_rejects_even_a_stale_due_instant(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual")
    records = jobs.load_jobs()
    records[0]["next_run_at"] = "2000-01-01T00:00:00+00:00"
    jobs.save_jobs(records)
    assert jobs.get_due_jobs() == []
    assert not jobs.claim_job_for_fire(job["id"])
