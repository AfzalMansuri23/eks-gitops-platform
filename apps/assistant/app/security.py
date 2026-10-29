"""Secure-by-default HTTP layer: security headers, a request body cap and a
per-IP rate limit. No CORS middleware on purpose: the UI is served from the
same origin, so browsers block cross-origin calls by default."""

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

LUCIDE = "https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js"

CSP = "; ".join(
    [
        "default-src 'self'",
        f"script-src 'self' {LUCIDE}",
        # inline style attributes in the pages (animation delays, small tweaks)
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

HEADERS = [
    (b"content-security-policy", CSP.encode()),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
]


class SecurityMiddleware:
    """Pure ASGI: adds the headers to every response and refuses request bodies
    over max_body bytes (413) before anything parses them."""

    def __init__(self, app, max_body: int = 16 * 1024):
        self.app = app
        self.max_body = max_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                names = {k for k, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [h for h in HEADERS if h[0] not in names]
            await send(message)

        length = dict(scope.get("headers", [])).get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > self.max_body):
            return await self._too_large(send_with_headers)

        received = 0

        async def capped_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body:
                    raise _BodyTooLarge
            return message

        try:
            await self.app(scope, capped_receive, send_with_headers)
        except _BodyTooLarge:
            await self._too_large(send_with_headers)

    @staticmethod
    async def _too_large(send):
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b'{"detail":"request too large"}'})


class _BodyTooLarge(Exception):
    pass


class RateLimiter:
    """Sliding window per client IP, in memory (per pod). Behind an ingress the
    client IP comes from uvicorn's --proxy-headers, which only trusts
    --forwarded-allow-ips."""

    def __init__(self, limit: int, window: float = 60.0, max_clients: int = 10_000):
        self.limit = limit
        self.window = window
        self.max_clients = max_clients
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if len(self.hits) > self.max_clients:
                self._prune(now)
            q = self.hits[key]
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def _prune(self, now: float):
        for key in [k for k, q in self.hits.items() if not q or q[-1] <= now - self.window]:
            del self.hits[key]
        while len(self.hits) > self.max_clients:
            del self.hits[next(iter(self.hits))]


limiter = RateLimiter(int(os.getenv("ASK_RATE_LIMIT", "30")), float(os.getenv("ASK_RATE_WINDOW", "60")))


def rate_limit(request: Request):
    from .observability import RATE_LIMITED

    client = request.client.host if request.client else "unknown"
    if limiter.limit > 0 and not limiter.allow(client):
        RATE_LIMITED.inc()
        raise HTTPException(status_code=429, detail="too many requests", headers={"Retry-After": str(int(limiter.window))})
