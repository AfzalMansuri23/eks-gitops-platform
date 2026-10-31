from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import kb

BASE = Path(__file__).parent
PAGES = BASE / "pages"

app = FastAPI(title="ExitZero")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


class AskRequest(BaseModel):
    error: str = Field(min_length=3, max_length=4000)


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


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    hits = kb.search(req.error)
    if not hits:
        return AskResponse(found=False, backend="keyword-demo")
    best = hits[0]
    return AskResponse(
        found=True,
        tool=best.tool,
        cause=best.cause,
        fix=best.fix,
        commands=list(best.commands),
        related=[h.title for h in hits[1:]],
        sources=[Source(title=h.source, snippet=h.title) for h in hits],
        backend="keyword-demo",
    )
