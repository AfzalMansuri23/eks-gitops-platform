"""JSON logs and Prometheus metrics, same setup as apps/api.

Pasted errors can contain secrets, so the error text itself is never logged:
only its length and a keyed short hash (the key is random per process unless
LOG_HASH_KEY is set), which is enough to spot repeats without being reversible.
"""

import hashlib
import logging
import os
import secrets
import sys

from prometheus_client import Counter, Histogram
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

log = logging.getLogger("exitzero")

ASKS = Counter("exitzero_asks_total", "Questions answered, by result and matched tool", ["result", "tool"])
RETRIEVAL_SECONDS = Histogram(
    "exitzero_retrieval_seconds",
    "Time spent in retrieval per question",
    ["retriever"],
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)
RATE_LIMITED = Counter("exitzero_rate_limited_total", "Questions rejected by the per-IP rate limit")
LLM_REQUESTS = Counter("exitzero_llm_requests_total", "Agent runs by outcome", ["outcome"])
LLM_SECONDS = Histogram(
    "exitzero_llm_seconds", "Time spent in the agent per question",
    buckets=(0.5, 1, 2, 4, 8, 15, 30, 60),
)
LLM_TOKENS = Counter("exitzero_llm_tokens_total", "Tokens used by the agent", ["kind"])
LLM_TOOL_CALLS = Counter("exitzero_llm_tool_calls_total", "Runbook tool calls made by the agent", ["tool"])
REDACTIONS = Counter("exitzero_redactions_total", "Secrets removed from pasted errors before they left the process")

_HASH_KEY = os.getenv("LOG_HASH_KEY", "").encode() or secrets.token_bytes(16)


def fingerprint(text: str) -> dict:
    digest = hashlib.blake2b(text.encode(), key=_HASH_KEY, digest_size=6).hexdigest()
    return {"input_chars": len(text), "input_hash": digest}
