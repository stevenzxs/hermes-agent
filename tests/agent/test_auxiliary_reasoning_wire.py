"""The resolved wire, not a URL heuristic, owns private reasoning arguments."""

import asyncio
import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from openai import AsyncOpenAI, OpenAI

from agent import auxiliary_client as aux


KIMI_BASE = "https://api.kimi.com/coding/v1"


@pytest.mark.parametrize("wire", ["sync", "async", "stream", "native"])
@pytest.mark.parametrize("reasoning", [{"enabled": False}, {"enabled": True, "effort": "high"}])
def test_resolved_wire_preserves_reasoning_without_leaking_private_kwargs(wire, reasoning):
    kwargs = aux._build_call_kwargs(
        "kimi-coding", "kimi-for-coding", [{"role": "user", "content": "hello"}],
        base_url=KIMI_BASE, reasoning_config=reasoning,
    )
    original = copy.deepcopy(kwargs)
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, request=request, json={
            "id": "fixture", "object": "chat.completion", "created": 0,
            "model": "kimi-for-coding", "choices": [],
        })

    if wire == "async":
        async def run():
            async def async_respond(request):
                return respond(request)
            async with AsyncOpenAI(
                api_key="fixture", base_url=KIMI_BASE,
                http_client=httpx.AsyncClient(transport=httpx.MockTransport(async_respond)),
            ) as client:
                await aux._relay_async_completion(client, kwargs)
        asyncio.run(run())
    elif wire == "native":
        captured = []
        aux._relay_sync_completion(SimpleNamespace(), kwargs, create=captured.append)
        assert captured[0] is kwargs
        assert captured[0]["_reasoning_config"] == reasoning
    else:
        with OpenAI(
            api_key="fixture", base_url=KIMI_BASE,
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ) as client:
            if wire == "stream":
                aux._relay_sync_stream(client, {**kwargs, "stream": True}).close()
            else:
                aux._relay_sync_completion(client, kwargs)
    if wire != "native":
        assert len(requests) == 1
        assert "_reasoning_config" not in requests[0]
        if reasoning["enabled"]:
            assert requests[0]["reasoning_effort"] == "high"
        else:
            assert requests[0]["thinking"] == {"type": "disabled"}
    assert kwargs == original


@pytest.mark.parametrize("entrypoint", ["title", "approval", "async"])
def test_kimi_explicit_chat_background_tasks_reach_sdk(tmp_path, monkeypatch, entrypoint):
    """Real config, route resolution, consumers and SDK; only HTTP is replaced."""
    from agent.title_generator import generate_title
    from tools.approval_smart import _smart_approve

    runtime = {
        "provider": "kimi-coding", "model": "kimi-for-coding", "base_url": KIMI_BASE,
        "api_mode": "chat_completions", "api_key": "fixture",
    }
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("KIMI_API_KEY", "fixture")
    monkeypatch.setenv("KIMI_BASE_URL", KIMI_BASE)
    (tmp_path / "config.yaml").write_text(json.dumps({"model": {
        "provider": runtime["provider"], "default": runtime["model"],
        "base_url": KIMI_BASE, "api_mode": "chat_completions",
    }}), encoding="utf-8")
    requests = []

    def send(_client, request, **_kwargs):
        assert str(request.url) == KIMI_BASE + "/chat/completions"
        payload = json.loads(request.content)
        requests.append(payload)
        text = '{"title":"Repair auxiliary request routing"}' if entrypoint == "title" else "APPROVE"
        return httpx.Response(200, request=request, json={
            "id": "fixture", "object": "chat.completion", "created": 0,
            "model": runtime["model"], "choices": [{
                "index": 0, "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }],
        })

    async def async_send(client, request, **kwargs):
        return send(client, request, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", send)
    monkeypatch.setattr(httpx.AsyncClient, "send", async_send)
    aux.shutdown_cached_clients()
    aux._reset_aux_unhealthy_cache()
    try:
        if entrypoint == "title":
            assert generate_title("Repair the auxiliary model request", main_runtime=runtime) == (
                "Repair auxiliary request routing"
            )
        elif entrypoint == "approval":
            with aux.scoped_runtime_main(runtime):
                assert _smart_approve("python -c 'print(1)'", "script execution") == "approve"
        else:
            response = asyncio.run(aux.async_call_llm(
                task="session_search", main_runtime=runtime,
                messages=[{"role": "user", "content": "hello"}], reasoning_config={"enabled": False},
            ))
            assert response.choices[0].message.content == "APPROVE"
        assert len(requests) == 1
        assert requests[0]["thinking"] == {"type": "disabled"}
        assert "_reasoning_config" not in requests[0]
    finally:
        aux.shutdown_cached_clients()
        aux._reset_aux_unhealthy_cache()
