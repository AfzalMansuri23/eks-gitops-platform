import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

import anthropic

from . import kb, retrieval
from .agent import AgentError, make_agent
from .guard import check_answer, injection_signals
from .observability import (
    ASKS, GUARD_BLOCKED, GUARD_FLAGGED, INJECTION, LLM_REQUESTS, LLM_SECONDS, LLM_TOKENS, LLM_TOOL_CALLS, REDACTIONS, RETRIEVAL_SECONDS, fingerprint, log,
)
from .redact import redact
from .security import SecurityMiddleware, rate_limit

BASE = Path(__file__).parent
PAGES = BASE / "pages"
MAX_ERROR_CHARS = 4000

RETRIEVER = retrieval.make_retriever()
AGENT = make_agent(RETRIEVER)  # None unless LLM_BACKEND=anthropic

# API docs are off unless asked for: they load scripts from a CDN the CSP blocks
docs = os.getenv("ENABLE_DOCS", "false").lower() == "true"
app = FastAPI(
    title="ExitZero",
    docs_url="/docs" if docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if docs else None,
)
app.add_middleware(SecurityMiddleware, max_body=int(os.getenv("MAX_BODY_BYTES", "16384")))
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
Instrumentator(excluded_handlers=["/metrics", "/health", "/static.*"]).instrument(app).expose(app, include_in_schema=False)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # FastAPI's default 422 echoes the submitted input back; it may hold secrets
    errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "invalid")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    # type only: a message or traceback could carry the pasted text
    log.error("unhandled error", extra={"path": request.url.path, "error_type": type(exc).__name__})
    return JSONResponse(status_code=500, content={"detail": "internal error"})


class AskRequest(BaseModel):
    error: str = Field(min_length=3, max_length=MAX_ERROR_CHARS)


class Source(BaseModel):
    title: str
    snippet: str


class AskResponse(BaseModel):
    found: bool
    tool: str | None = None
    cause: str | None = None
    fix: str | None = None
    commands: list[str] = []
    related: list[str] = []
    sources: list[Source] = []
    backend: str
    score: float | None = None
    grounded: bool | None = None  # agent only: answer backed by a runbook
    redactions: int = 0  # secrets removed before the error was sent to the LLM, or from the answer
    command_risks: list[str] = []  # one per command: safe, sensitive or destructive
    blocked: int = 0  # unsafe commands removed by the safety filter


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tools")
def tool_list():
    return {"tools": kb.tools(), "entries": len(kb.ENTRIES)}


@app.get("/")
def landing():
    return FileResponse(PAGES / "index.html")


@app.get("/app")
def console():
    return FileResponse(PAGES / "console.html")


@app.get("/access")
def access():
    return FileResponse(PAGES / "access.html")


@app.get("/architecture")
def architecture():
    return FileResponse(PAGES / "architecture.html")


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(rate_limit)])
def ask(req: AskRequest):
    start = time.perf_counter()
    hits = RETRIEVER.search(req.error, 3)
    elapsed = time.perf_counter() - start
    RETRIEVAL_SECONDS.labels(RETRIEVER.name).observe(elapsed)

    answer = ask_agent(req.error, hits) if AGENT is not None else None
    if answer is None:
        answer = from_retrieval(hits)
    answer = guarded(answer)

    ASKS.labels("found" if answer.found else "miss", answer.tool or "none").inc()
    log.info(
        "ask",
        extra={
            **fingerprint(req.error),
            "found": answer.found,
            "tool": answer.tool,
            "score": answer.score,
            "backend": answer.backend,
            "blocked": answer.blocked,
            "retrieval_ms": round(elapsed * 1000, 2),
        },
    )
    return answer


def guarded(answer: AskResponse) -> AskResponse:
    """Last stop before the browser: drop unsafe commands, flag risky ones, scrub secrets."""
    if not answer.found:
        return answer
    checked = check_answer(answer.cause, answer.fix, answer.commands)
    for reason in checked.blocked:
        GUARD_BLOCKED.labels(reason).inc()
    for risk in checked.risks:
        if risk != "safe":
            GUARD_FLAGGED.labels(risk).inc()
    return answer.model_copy(update={
        "cause": checked.cause,
        "fix": checked.fix,
        "commands": checked.commands,
        "command_risks": checked.risks,
        "blocked": len(checked.blocked),
        "redactions": answer.redactions + checked.redactions,
    })


def from_retrieval(hits) -> AskResponse:
    if not hits:
        return AskResponse(found=False, backend=RETRIEVER.name)
    best, score = hits[0]
    return AskResponse(
        found=True,
        tool=best.tool,
        cause=best.cause,
        fix=best.fix,
        commands=list(best.commands),
        related=[h.title for h, _ in hits[1:]],
        sources=[Source(title=h.source, snippet=h.title) for h, _ in hits],
        backend=RETRIEVER.name,
        score=score,
    )


def ask_agent(error: str, hits) -> AskResponse | None:
    """Run the agent on the redacted error. None means: use the retrieval answer."""
    clean, redactions = redact(error)
    REDACTIONS.inc(redactions)
    signals = injection_signals(error)
    for kind in signals:
        INJECTION.labels(kind).inc()
    start = time.perf_counter()
    try:
        result = AGENT.ask(clean, [e for e, _ in hits])
        outcome = "ok"
    except AgentError as e:
        result, outcome = None, e.reason
    except anthropic.APIError as e:
        result, outcome = None, type(e).__name__
    seconds = time.perf_counter() - start
    LLM_SECONDS.observe(seconds)
    LLM_REQUESTS.labels(outcome).inc()
    log.info("agent", extra={"outcome": outcome, "llm_ms": round(seconds * 1000), "redactions": redactions,
                             "injection_signals": signals,
                             **({"model": result.model, "tool_calls": result.tool_calls, **result.usage} if result else {})})
    if result is None:
        return None
    for kind, n in result.usage.items():
        LLM_TOKENS.labels(kind.removesuffix("_tokens")).inc(n)
    for name in result.tool_calls:
        LLM_TOOL_CALLS.labels(name).inc()

    backend = f"{result.model} + runbooks" if result.grounded else f"{result.model} · general"
    if not result.found:
        return AskResponse(found=False, backend=result.model, redactions=redactions)
    used = {e.title for e in result.runbooks}
    return AskResponse(
        found=True,
        tool=result.tool,
        cause=result.cause,
        fix=result.fix,
        commands=result.commands,
        related=[e.title for e in result.runbooks[1:]] + [h.title for h, _ in hits if h.title not in used][:2],
        sources=[Source(title=e.source, snippet=e.title) for e in result.runbooks],
        backend=backend,
        grounded=result.grounded,
        redactions=redactions,
    )
