"""Pause is an admission gate, not cancellation of an existing execution."""
import pytest


@pytest.mark.parametrize("schedule", ["manual", "every 1h"])
@pytest.mark.parametrize("flags", [{}, {"manual": True}, {"force": True}])
def test_pause_rejects_all_new_claims(tmp_path, monkeypatch, schedule, flags):
    from cron import jobs
    from cron.fire_admission import capture_refusal

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule=schedule, paused=True)
    with capture_refusal() as refusal:
        assert not jobs.claim_job_for_fire(job["id"], **flags)
    assert refusal.code == "job_paused"
    assert jobs.get_job(job["id"])["enabled"] is False
    assert jobs.get_due_jobs() == []


@pytest.mark.parametrize("schedule", ["manual", "every 1h"])
def test_pause_keeps_live_claim_and_completion_paused(tmp_path, monkeypatch, schedule):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule=schedule)
    assert jobs.claim_job_for_fire(job["id"], manual=True)
    claim = jobs.get_job(job["id"])["fire_claim"]
    paused = jobs.pause_job(job["id"])
    assert paused["fire_claim"] == claim
    assert jobs.mark_job_run(job["id"], True, expected_fire_owner=claim["by"])
    saved = jobs.get_job(job["id"])
    assert saved["last_status"] == "ok"
    assert saved["enabled"] is False
    assert saved["state"] == "paused"
    assert saved["fire_claim"] is None


def test_resume_waits_for_next_rule_instead_of_replaying_paused_slot(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="every 1h")
    jobs.pause_job(job["id"])
    records = jobs.load_jobs()
    records[0]["next_run_at"] = "2000-01-01T00:00:00+00:00"
    jobs.save_jobs(records)
    saved = jobs.resume_job(job["id"])
    assert saved["next_run_at"] > jobs._hermes_now().isoformat()
    assert saved["enabled"] is True
    assert jobs.get_due_jobs() == []


def test_legacy_run_now_never_reactivates_paused_job(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="every 1h", paused=True)
    with pytest.raises(ValueError, match="paused"):
        jobs.trigger_job(job["id"])
    assert jobs.get_job(job["id"])["enabled"] is False


@pytest.mark.parametrize("claim_at,expected", [("2000-01-01T00:00:00+00:00", False), (None, True)])
def test_readback_exposes_live_execution_not_stale_claim(tmp_path, monkeypatch, claim_at, expected):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual", paused=True)
    rows = jobs.load_jobs()
    rows[0]["fire_claim"] = {"at": claim_at or jobs._hermes_now().isoformat(), "by": "other-host:1"}
    jobs.save_jobs(rows)
    assert jobs.get_job(job["id"])["execution_running"] is expected
    assert jobs.list_jobs(include_disabled=True)[0]["execution_running"] is expected


def test_readback_keeps_real_long_running_execution_visible(tmp_path, monkeypatch):
    from cron import jobs, scheduler

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual", paused=True)
    monkeypatch.setattr(scheduler, "is_job_running", lambda jid: jid == job["id"])
    assert jobs.get_job(job["id"])["execution_running"] is True


def test_readback_does_not_report_running_when_probe_fails(tmp_path, monkeypatch):
    from cron import jobs, scheduler

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual", paused=True)

    def unavailable(jid):
        raise RuntimeError("probe unavailable")

    monkeypatch.setattr(scheduler, "is_job_running", unavailable)
    assert jobs.get_job(job["id"])["execution_running"] is False
