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

from . import kb, retrieval
from .observability import ASKS, RETRIEVAL_SECONDS, fingerprint, log
from .security import SecurityMiddleware, rate_limit

BASE = Path(__file__).parent
PAGES = BASE / "pages"
MAX_ERROR_CHARS = 4000

RETRIEVER = retrieval.make_retriever()

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


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(rate_limit)])
def ask(req: AskRequest):
    start = time.perf_counter()
    hits = RETRIEVER.search(req.error, 3)
    elapsed = time.perf_counter() - start
    RETRIEVAL_SECONDS.labels(RETRIEVER.name).observe(elapsed)

    best, score = hits[0] if hits else (None, None)
    ASKS.labels("found" if best else "miss", best.tool if best else "none").inc()
    log.info(
        "ask",
        extra={
            **fingerprint(req.error),
            "found": best is not None,
            "tool": best.tool if best else None,
            "score": score,
            "retriever": RETRIEVER.name,
            "retrieval_ms": round(elapsed * 1000, 2),
        },
    )
    if best is None:
        return AskResponse(found=False, backend=RETRIEVER.name)
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
