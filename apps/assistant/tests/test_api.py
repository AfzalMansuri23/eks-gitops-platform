import logging

import pytest
from fastapi.testclient import TestClient

from app import kb
from app.main import app
from app.security import limiter

SECRET = "FAKESECRET_9f8e7d"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(limiter, "limit", 1000)
    limiter.hits.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_tools(client):
    body = client.get("/tools").json()
    assert body["tools"] == kb.tools() and body["entries"] == len(kb.ENTRIES)


@pytest.mark.parametrize("path", ["/", "/app", "/access"])
def test_pages(client, path):
    r = client.get(path)
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]


def test_ask_found_keeps_ui_schema(client):
    body = client.post("/ask", json={"error": "Error: Error acquiring the state lock LockID: abc"}).json()
    assert body["found"] is True and body["tool"] == "Terraform"
    for key in ("cause", "fix", "commands", "related", "sources", "backend", "score"):
        assert key in body
    assert body["backend"] == "hybrid"
    assert body["sources"][0]["snippet"] == "Terraform state is locked"


def test_ask_paraphrase(client):
    body = client.post("/ask", json={"error": "terraform says someone else is holding the lock on the state file"}).json()
    assert body["found"] and "state is locked" in body["sources"][0]["snippet"]


def test_ask_not_found(client):
    body = client.post("/ask", json={"error": "how do I bake sourdough bread"}).json()
    assert body == {"found": False, "tool": None, "cause": None, "fix": None, "commands": [], "related": [],
                    "sources": [], "backend": "hybrid", "score": None}


@pytest.mark.parametrize("payload", [{}, {"error": "ab"}, {"error": 5}, {"error": "x" * 4001}, {"wrong": "field"}])
def test_ask_validation(client, payload):
    r = client.post("/ask", json=payload)
    assert r.status_code == 422
    assert all(set(e) == {"loc", "msg"} for e in r.json()["detail"])


def test_validation_error_does_not_echo_input(client):
    r = client.post("/ask", json={"error": SECRET + "x" * 4000})
    assert r.status_code == 422 and SECRET not in r.text


def test_body_too_large(client):
    r = client.post("/ask", content=b'{"error":"' + b"a" * 20000 + b'"}', headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json() == {"detail": "request too large"}


def test_bad_json(client):
    r = client.post("/ask", content=b"{not json", headers={"content-type": "application/json"})
    assert r.status_code == 422


def test_security_headers(client):
    h = client.get("/").headers
    csp = h["content-security-policy"]
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert "https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js" in csp
    assert h["x-content-type-options"] == "nosniff"
    assert h["referrer-policy"] == "no-referrer"


def test_no_cors(client):
    r = client.post("/ask", json={"error": "OOMKilled"}, headers={"origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
    r = client.options("/ask", headers={"origin": "https://evil.example", "access-control-request-method": "POST"})
    assert "access-control-allow-origin" not in r.headers


def test_docs_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(limiter, "limit", 3)
    codes = [client.post("/ask", json={"error": "OOMKilled"}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    r = client.post("/ask", json={"error": "OOMKilled"})
    assert r.json() == {"detail": "too many requests"} and r.headers["retry-after"]


def test_unhandled_error_is_generic(monkeypatch):
    from app import main

    def boom(text, k):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(main.RETRIEVER, "search", boom)
    r = TestClient(app, raise_server_exceptions=False).post("/ask", json={"error": "OOMKilled"})
    assert r.status_code == 500 and r.json() == {"detail": "internal error"} and SECRET not in r.text


def test_logs_never_contain_input(client, caplog):
    with caplog.at_level(logging.INFO):
        client.post("/ask", json={"error": f"Error acquiring the state lock password={SECRET}"})
        client.post("/ask", json={"error": SECRET + " gibberish qwerty"})
    asks = [r for r in caplog.records if r.getMessage() == "ask"]
    assert len(asks) == 2
    for record in caplog.records:
        assert SECRET not in record.getMessage() and SECRET not in str(record.__dict__)
    assert asks[0].input_chars == len(f"Error acquiring the state lock password={SECRET}")
    assert len(asks[0].input_hash) == 12


def test_metrics(client):
    client.post("/ask", json={"error": "OOMKilled"})
    client.post("/ask", json={"error": "how do I bake sourdough bread"})
    text = client.get("/metrics").text
    assert 'exitzero_asks_total{result="found",tool="Kubernetes"}' in text
    assert 'exitzero_asks_total{result="miss",tool="none"}' in text
    assert 'exitzero_retrieval_seconds_count{retriever="hybrid"}' in text
    assert "http_requests_total" in text
