"""Opening a round is idempotent and never reactivates historical records."""

def test_new_round_keeps_original_and_reuses_request(tmp_path, monkeypatch):
    from cron import jobs
    from cron.job_rounds import open_round

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    original = jobs.create_job(prompt="x", schedule="manual", repeat=1)
    assert jobs.claim_job_for_fire(original["id"], manual=True)
    jobs.mark_job_run(original["id"], "ok")
    before = jobs.get_job(original["id"])
    new = open_round(original["id"], "request-123")
    assert new["id"] != original["id"]
    assert new["round_parent_id"] == original["id"]
    assert new["enabled"] is False
    assert new["repeat"] == {"times": 1, "completed": 0}
    assert new["next_run_at"] is None
    assert open_round(original["id"], "request-123")["id"] == new["id"]
    assert jobs.get_job(original["id"]) == before
    assert len(jobs.load_jobs()) == 2


def test_concurrent_new_round_requests_create_one_successor(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from cron import jobs
    from cron.job_rounds import open_round

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    original = jobs.create_job(prompt="x", schedule="manual", repeat=1)
    assert jobs.claim_job_for_fire(original["id"], manual=True)
    jobs.mark_job_run(original["id"], "ok")
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: open_round(original["id"], "same-request")["id"], range(2)))
    assert ids[0] == ids[1]
    assert len(jobs.load_jobs()) == 2
