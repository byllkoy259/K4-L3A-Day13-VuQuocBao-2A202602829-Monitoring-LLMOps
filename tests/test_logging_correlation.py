from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx

from app import logging_config
from app.logging_config import scrub_event
from app.main import app

BODY = {
    "user_id": "student-01",
    "session_id": "session-01",
    "feature": "qa",
    "message": "My email is student@vinuni.edu.vn, phone 0901234567, CCCD 012345678901, card 4111 1111 1111 1111",
}


def _post(headers: dict[str, str] | None = None, times: int = 1) -> list[httpx.Response]:
    async def run() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return [await client.post("/chat", json=BODY, headers=headers) for _ in range(times)]

    return asyncio.run(run())


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_generated_request_id_and_headers(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    first, second = _post(times=2)
    for resp in (first, second):
        assert re.fullmatch(r"req-[0-9a-f]{8}", resp.headers["x-request-id"])
        assert int(resp.headers["x-response-time-ms"]) >= 0
        assert resp.json()["correlation_id"] == resp.headers["x-request-id"]
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_incoming_request_id_is_reused_and_logged(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    (resp,) = _post(headers={"x-request-id": "req-deadbeef"})
    assert resp.headers["x-request-id"] == "req-deadbeef"
    api_events = [e for e in _read(log_path) if e.get("service") == "api"]
    assert api_events and all(e["correlation_id"] == "req-deadbeef" for e in api_events)


def test_unsafe_request_id_is_replaced(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    (resp,) = _post(headers={"x-request-id": "bad id with spaces"})
    assert re.fullmatch(r"req-[0-9a-f]{8}", resp.headers["x-request-id"])


def test_logs_are_enriched_and_scrubbed_without_context_leak(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    first, second = _post(times=2)
    events = _read(log_path)
    api_events = [e for e in events if e.get("service") == "api"]
    for e in api_events:
        for field in ("user_id_hash", "session_id", "feature", "model", "env"):
            assert e.get(field), f"{field} missing in {e['event']}"
    assert {e["correlation_id"] for e in api_events} == {
        first.headers["x-request-id"],
        second.headers["x-request-id"],
    }
    raw = log_path.read_text(encoding="utf-8")
    for secret in ("student@vinuni.edu.vn", "0901234567", "012345678901", "4111 1111 1111 1111"):
        assert secret not in raw


def test_scrub_event_handles_nested_values_and_keeps_identifiers() -> None:
    out = scrub_event(
        None,
        "info",
        {
            "event": "x",
            "detail": "mail a@b.com",
            "user_id_hash": "123456789012",
            "payload": {"items": ["call 0901234567"], "n": 1},
        },
    )
    assert "a@b.com" not in out["detail"]
    assert out["user_id_hash"] == "123456789012"
    assert "0901234567" not in out["payload"]["items"][0]
    assert out["payload"]["n"] == 1
