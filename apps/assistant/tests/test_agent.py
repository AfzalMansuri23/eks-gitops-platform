"""Agent tests with a scripted fake client: no API key, no network, no cost."""

import json
import logging
from types import SimpleNamespace as NS

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.agent import Agent, AgentError
from app.redact import redact
from app.security import limiter

SECRET = "FAKESECRET_agent_9f8e"
LOCK = "Terraform state is locked"


def text(data):
    return NS(type="text", text=json.dumps(data))


def tool_use(name, args, id="tu_1"):
    return NS(type="tool_use", name=name, input=args, id=id)


def reply(*blocks, stop="end_turn"):
    return NS(content=list(blocks), stop_reason=stop, model="claude-opus-5-5",
              usage=NS(input_tokens=1200, output_tokens=300))


def answer(**over):
    base = {"found": True, "grounded": True, "tool": "Terraform", "cause": "Another run holds the lock.",
            "fix": "Wait for it, or force-unlock with the lock ID.", "commands": ["terraform force-unlock <id>"],
            "runbooks": [LOCK]}
    return {**base, **over}


class FakeClient:
    """Plays back scripted responses and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs, default=lambda o: o.__dict__)))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(limiter, "limit", 1000)
    limiter.hits.clear()


def use(monkeypatch, fake):
    monkeypatch.setattr(main, "AGENT", Agent(main.RETRIEVER, client=fake))


# ---- redaction

@pytest.mark.parametrize("raw,kind,secret", [
    ("aws_access_key_id=AKIAIOSFODNN7EXAMPLE", "aws-access-key", "AKIAIOSFODNN7EXAMPLE"),
    ("aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "aws-secret", "wJalrXUtnFEMI"),
    ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456", "auth-header", "abcdefghijklmnop"),
    ("postgres://app:Sup3rS3cret@db:5432/shop", "url-credentials", "Sup3rS3cret"),
    ("DB_PASSWORD=hunter2hunter2", "assignment", "hunter2"),
    ("GITHUB_TOKEN=abcd1234efgh", "assignment", "abcd1234"),
    ("token: ghp_abcdefghijklmnopqrstuvwxyz0123456789", "github-token", "ghp_abcdefgh"),
    ("x-api-key: sk-ant-api03-abcdefghijklmnop", "anthropic-key", "sk-ant-api03"),
    ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U", "jwt", "dozjgNryP4J3"),
    ("-----BEGIN RSA PRIVATE KEY-----\nMIIEowSECRETBODY\n-----END RSA PRIVATE KEY-----", "private-key", "SECRETBODY"),
])
def test_redacts_common_secrets(raw, kind, secret):
    out, n = redact(f"error near {raw} in config")
    assert n >= 1 and f"[REDACTED:{kind}]" in out and secret not in out


def test_redaction_keeps_ordinary_errors_intact():
    msg = "Error: Error acquiring the state lock LockID: abc\nOOMKilled Exit Code: 137 pod api-7d9f"
    assert redact(msg) == (msg, 0)


def test_redaction_does_not_double_count():
    out, n = redact("token=Bearer abcdefghijklmnopqrstuvwxyz123456")
    assert n == 1 and out.count("REDACTED") == 1


# ---- agent loop

def test_agent_uses_tool_then_answers(monkeypatch, client):
    fake = FakeClient(
        reply(tool_use("get_runbook", {"title": LOCK}), stop="tool_use"),
        reply(text(answer())),
    )
    use(monkeypatch, fake)
    body = client.post("/ask", json={"error": "terraform says someone else holds the state lock"}).json()
    assert body["found"] and body["grounded"] and body["tool"] == "Terraform"
    assert body["backend"] == "claude-opus-5-5 + runbooks"
    assert body["sources"][0]["snippet"] == LOCK
    # the tool result sent back holds the real runbook entry
    tool_result = fake.requests[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and LOCK in tool_result["content"] and not tool_result["is_error"]


def test_request_shape(monkeypatch, client):
    fake = FakeClient(reply(text(answer())))
    use(monkeypatch, fake)
    client.post("/ask", json={"error": "Error acquiring the state lock"})
    req = fake.requests[0]
    assert req["model"] == "claude-opus-5-5"
    assert req["fallbacks"] == "default" and req["betas"] == ["server-side-fallback-2026-07-01"]
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "tool_choice" not in req and "thinking" not in req
    assert {t["name"] for t in req["tools"]} == {"search_runbooks", "get_runbook"}
    assert all(t["strict"] for t in req["tools"])
    assert "<pasted_error>" in req["messages"][0]["content"] and LOCK in req["messages"][0]["content"]


def test_made_up_sources_are_dropped(monkeypatch, client):
    use(monkeypatch, FakeClient(reply(text(answer(runbooks=["A runbook that does not exist"])))))
    body = client.post("/ask", json={"error": "Error acquiring the state lock"}).json()
    assert body["found"] and body["grounded"] is False and body["sources"] == []
    assert body["backend"] == "claude-opus-5-5 · general"


def test_general_answer_without_runbook(monkeypatch, client):
    use(monkeypatch, FakeClient(reply(text(answer(grounded=False, runbooks=[], tool="Nomad")))))
    body = client.post("/ask", json={"error": "nomad: allocation failed, no nodes were eligible"}).json()
    assert body["found"] and body["grounded"] is False and body["tool"] == "Nomad"


def test_not_an_error(monkeypatch, client):
    use(monkeypatch, FakeClient(reply(text(answer(found=False, grounded=False, tool="", cause="", fix="", commands=[], runbooks=[])))))
    body = client.post("/ask", json={"error": "how do I bake sourdough bread"}).json()
    assert body["found"] is False and body["sources"] == []


def test_commands_are_capped(monkeypatch, client):
    use(monkeypatch, FakeClient(reply(text(answer(commands=[f"echo {i}" for i in range(20)])))))
    body = client.post("/ask", json={"error": "Error acquiring the state lock"}).json()
    assert len(body["commands"]) == 8


def test_unknown_runbook_title_is_a_tool_error():
    agent = Agent(main.RETRIEVER, client=FakeClient())
    content, is_error = agent.run_tool("get_runbook", {"title": "nope"})
    assert is_error and "exact title" in content
    content, is_error = agent.run_tool("search_runbooks", {"query": "terraform state lock"})
    assert not is_error and LOCK in content


# ---- failures fall back to retrieval

def api_error():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(request=request)


@pytest.mark.parametrize("make", [
    lambda: [api_error()],
    lambda: [reply(stop="refusal")],
    lambda: [reply(text("not json"))],
    lambda: [reply(tool_use("search_runbooks", {"query": "x"}), stop="tool_use")] * 4,
])
def test_failures_fall_back_to_retrieval(monkeypatch, client, make):
    use(monkeypatch, FakeClient(*make()))
    body = client.post("/ask", json={"error": "Error: Error acquiring the state lock LockID: abc"}).json()
    assert body["found"] and body["backend"] == "hybrid" and body["sources"][0]["snippet"] == LOCK


def test_agent_raises_on_too_many_turns():
    loop = [reply(tool_use("search_runbooks", {"query": "x"}), stop="tool_use")] * 4
    with pytest.raises(AgentError, match="too_many_turns"):
        Agent(main.RETRIEVER, client=FakeClient(*loop)).ask("x", [])


# ---- secrets never leave the process, never reach logs

def test_secret_is_redacted_before_sending_and_never_logged(monkeypatch, client, caplog):
    fake = FakeClient(reply(text(answer())))
    use(monkeypatch, fake)
    with caplog.at_level(logging.INFO):
        body = client.post("/ask", json={"error": f"Error acquiring the state lock\nDB_PASSWORD={SECRET}"}).json()
    assert body["redactions"] == 1
    assert SECRET not in json.dumps(fake.requests)
    assert "[REDACTED:assignment]" in fake.requests[0]["messages"][0]["content"]
    for record in caplog.records:
        assert SECRET not in record.getMessage() and SECRET not in str(record.__dict__)


def test_agent_metrics(monkeypatch, client):
    use(monkeypatch, FakeClient(reply(tool_use("get_runbook", {"title": LOCK}), stop="tool_use"), reply(text(answer()))))
    client.post("/ask", json={"error": "Error acquiring the state lock"})
    m = client.get("/metrics").text
    assert 'exitzero_llm_requests_total{outcome="ok"}' in m
    assert 'exitzero_llm_tokens_total{kind="input"}' in m
    assert 'exitzero_llm_tool_calls_total{tool="get_runbook"}' in m


def test_agent_off_by_default():
    assert main.AGENT is None
