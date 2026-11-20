"""Dashboard transports retain actionable atomic admission diagnostics."""

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_http_refusal_has_structured_and_legacy_fields(monkeypatch):
    import json
    from hermes_cli.web_routers import cron

    async def reject(*args):
        raise HTTPException(status_code=409, detail="Execution limit reached",
                            headers={"X-Cron-Error-Code": "execution_limit_reached"})
    monkeypatch.setattr(cron, "_run_cron_dashboard_io", reject)
    response = await cron.trigger_cron_job("finished")
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "code": "execution_limit_reached", "message": "Execution limit reached",
        "detail": "Execution limit reached"}


def test_completed_store_refusal_crosses_real_provider_and_dashboard(tmp_path, monkeypatch):
    from cron import jobs
    from cron.scheduler_provider import InProcessCronScheduler
    from hermes_cli import web_server_cron
    from hermes_cli.web_routers import cron

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="never execute", schedule="every 1h", repeat=1)
    records = jobs.load_jobs()
    records[0].update(state="completed", enabled=False, next_run_at=None,
                      repeat={"times": 1, "completed": 1})
    jobs.save_jobs(records)
    monkeypatch.setattr(cron, "_job_profile", lambda *args: "default")
    monkeypatch.setattr(cron, "_call_cron_for_profile",
                        lambda profile, method, jid: getattr(jobs, method)(jid))
    monkeypatch.setattr(web_server_cron, "_cron_profile_home", lambda profile: (profile, tmp_path))
    monkeypatch.setattr("cron.scheduler_provider.resolve_cron_scheduler", InProcessCronScheduler)
    monkeypatch.setattr(cron, "_fire_cron_job_for_profile", web_server_cron._fire_cron_job_for_profile)
    with pytest.raises(HTTPException) as error:
        cron._trigger_cron_job_sync(job["id"], "default")
    assert error.value.headers["X-Cron-Error-Code"] == "execution_limit_reached"
    assert jobs.get_job(job["id"]).get("fire_claim") is None


def test_trigger_returns_atomic_refusal_and_legacy_detail(monkeypatch):
    from cron.fire_admission import refuse
    from hermes_cli.web_routers import cron

    job = {"id": "done", "enabled": False, "state": "completed"}
    monkeypatch.setattr(cron, "_job_profile", lambda *args: "worker")
    monkeypatch.setattr(cron, "_call_cron_for_profile", lambda *args: dict(job))

    def fire(*args, **kwargs):
        return refuse("execution_limit_reached")

    monkeypatch.setattr(cron, "_fire_cron_job_for_profile", fire)
    with pytest.raises(HTTPException) as error:
        cron._trigger_cron_job_sync("done", "worker")
    assert error.value.status_code == 409
    assert "execution limit" in error.value.detail
    assert error.value.headers["X-Cron-Error-Code"] == "execution_limit_reached"


def test_legacy_provider_conflict_does_not_invent_running_reason(monkeypatch):
    from hermes_cli.web_routers import cron

    monkeypatch.setattr(cron, "_job_profile", lambda *args: "worker")
    monkeypatch.setattr(cron, "_call_cron_for_profile", lambda *args: {"id": "x"})
    monkeypatch.setattr(cron, "_fire_cron_job_for_profile", lambda *args, **kwargs: False)
    with pytest.raises(HTTPException) as error:
        cron._trigger_cron_job_sync("x", "worker")
    assert error.value.headers["X-Cron-Error-Code"] == "claim_conflict"
    assert "already running" not in error.value.detail
