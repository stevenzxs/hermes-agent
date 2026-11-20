"""Round API uses the selected profile and rejects malformed requests without writes."""
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def request(body):
    async def receive():
        return {"type": "http.request", "body": json.dumps(body).encode()}
    return Request({"type": "http", "method": "POST", "path": "/"}, receive)


@pytest.mark.asyncio
async def test_round_endpoint_scopes_store_and_leaves_original(tmp_path, monkeypatch):
    from cron import jobs
    from hermes_cli import web_server_cron
    from hermes_cli.web_routers import cron

    home = tmp_path / "worker"
    home.mkdir()
    with web_server_cron._cron_store_scope(home):
        original = jobs.create_job(prompt="never run", schedule="manual", repeat=1)
        assert jobs.claim_job_for_fire(original["id"], manual=True)
        jobs.mark_job_run(original["id"], "ok")
        before = jobs.get_job(original["id"])
    monkeypatch.setattr(cron, "_job_profile", lambda *args: "worker")
    monkeypatch.setattr(cron, "_cron_profile_home", lambda profile: (profile, home))
    successor = await cron.new_cron_round(original["id"], request({"request_id": "round-request"}), "worker")
    with web_server_cron._cron_store_scope(home):
        assert jobs.get_job(original["id"]) == before
        assert jobs.get_job(successor["id"])["enabled"] is False
    assert not (tmp_path / "cron" / "jobs.json").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [[], None, {}, {"request_id": 123}])
async def test_invalid_round_body_is_400(body):
    from hermes_cli.web_routers import cron

    with pytest.raises(HTTPException) as error:
        await cron.new_cron_round("job", request(body))
    assert error.value.status_code == 400
