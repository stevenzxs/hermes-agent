"""Dashboard automatic start does not execute; manual start never resumes pause."""
import pytest
from fastapi import HTTPException


@pytest.mark.parametrize("schedule", ["manual", "every 1h"])
def test_dashboard_paused_trigger_refused_without_dispatch(tmp_path, monkeypatch, schedule):
    from cron import jobs
    from hermes_cli.web_routers import cron

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule=schedule, paused=True)
    monkeypatch.setattr(cron, "_job_profile", lambda *args: "default")
    monkeypatch.setattr(cron, "_call_cron_for_profile", lambda p, method, jid: getattr(jobs, method)(jid))
    fired = []
    monkeypatch.setattr(cron, "_fire_cron_job_for_profile", lambda *a, **kw: fired.append(kw) or True)
    with pytest.raises(HTTPException) as error:
        cron._trigger_cron_job_sync(job["id"])
    assert error.value.headers["X-Cron-Error-Code"] == "job_paused"
    assert fired == []


def test_dashboard_automatic_start_keeps_future_slot_without_fire(tmp_path, monkeypatch):
    from cron import jobs
    from hermes_cli.web_routers import cron

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="every 1h")
    monkeypatch.setattr(cron, "_job_profile", lambda *args: "default")
    monkeypatch.setattr(cron, "_call_cron_for_profile", lambda p, method, jid: getattr(jobs, method)(jid))
    fired = []
    monkeypatch.setattr(cron, "_fire_cron_job_for_profile", lambda *a, **kw: fired.append(kw) or True)
    result = cron._trigger_cron_job_sync(job["id"])
    assert fired == []
    assert result["next_run_at"] == job["next_run_at"]
    assert result["repeat"] == job["repeat"]
