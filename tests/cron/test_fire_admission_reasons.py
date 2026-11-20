"""Refusal diagnostics describe the atomic decision, without changing bool callers."""

import pytest


def test_completed_claim_reports_exhausted_without_reactivating(tmp_path, monkeypatch):
    from cron import jobs
    from cron.fire_admission import capture_refusal

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="every 1h", repeat=1)
    records = jobs.load_jobs()
    records[0].update(state="completed", enabled=False, next_run_at=None,
                      repeat={"times": 1, "completed": 1})
    jobs.save_jobs(records)
    before = jobs.get_job(job["id"])
    with capture_refusal() as refusal:
        assert jobs.claim_job_for_fire(job["id"], force=True) is False
    assert refusal.code == "execution_limit_reached"
    assert jobs.get_job(job["id"]) == before


@pytest.mark.parametrize("paused", [True, False])
def test_claim_reports_paused_or_live_lease(tmp_path, monkeypatch, paused):
    from cron import jobs
    from cron.fire_admission import capture_refusal

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="every 1h")
    if paused:
        jobs.pause_job(job["id"])
    else:
        assert jobs.claim_job_for_fire(job["id"]) is True
    with capture_refusal() as refusal:
        assert jobs.claim_job_for_fire(job["id"]) is False
    assert refusal.code == ("job_paused" if paused else "job_running")


def test_refusal_capture_is_nested_and_request_scoped(tmp_path, monkeypatch):
    from cron import jobs
    from cron.fire_admission import capture_refusal

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="every 1h")
    jobs.pause_job(job["id"])
    with capture_refusal() as outer:
        assert jobs.claim_job_for_fire(job["id"]) is False
        with capture_refusal() as inner:
            assert jobs.claim_job_for_fire(job["id"], force=True) is False
        assert inner.code == "job_paused"
    assert outer.code == "job_paused"
