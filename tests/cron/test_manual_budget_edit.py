"""An edit cannot reset consumed count or grant a spent finite job an implicit run."""
import pytest


def test_repeat_edit_cannot_reset_consumed_counter(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual", repeat=3)
    assert jobs.claim_job_for_fire(job["id"], manual=True)
    jobs.mark_job_run(job["id"], "ok")
    with pytest.raises(ValueError, match="completed"):
        jobs.update_job(job["id"], {"repeat": {"times": 3, "completed": 0}})


def test_lowering_limit_to_consumed_retires_without_dispatch(tmp_path, monkeypatch):
    from cron import jobs

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    job = jobs.create_job(prompt="x", schedule="manual", repeat=3)
    assert jobs.claim_job_for_fire(job["id"], manual=True)
    jobs.mark_job_run(job["id"], "ok")
    saved = jobs.update_job(job["id"], {"repeat": 1})
    assert saved["state"] == "completed"
    assert not saved["enabled"]
    assert not jobs.claim_job_for_fire(job["id"], manual=True)
