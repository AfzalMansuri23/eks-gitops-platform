import logging
import sys

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        reserved_attrs=jsonlogger.RESERVED_ATTRS + ("color_message", "taskName"),
    )
)
logging.basicConfig(level=logging.INFO, handlers=[handler])

for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.propagate = False

log = logging.getLogger("api")

app = FastAPI()

Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    log.info("health check")
    return {"status": "ok"}
