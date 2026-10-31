# ExitZero: multi-stage build.
# builder: install deps, download the embedding model, pre-compute the runbook vectors.
# runtime: only the venv, the model, the vectors, app/ and knowledge/. Runs offline as a non-root user.
# The base is pinned by digest; behind a flaky Docker Hub connection, pull it from mirror.gcr.io/library/python first.

ARG PYTHON_IMAGE=python:3.13.18-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb

FROM ${PYTHON_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FASTEMBED_CACHE_PATH=/opt/models \
    EMBED_CACHE_DIR=/opt/vectors

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# model and vectors are baked in, so the pod needs no internet at runtime
COPY app/ app/
COPY knowledge/ knowledge/
# then make them world-readable for the non-root user, and drop pip from the venv
RUN python -c "from app.retrieval import EmbeddingRetriever; r = EmbeddingRetriever(); print('vectors', r.matrix.shape)" \
 && chmod -R a+rX /opt/models /opt/vectors \
 && python -m pip uninstall -y pip


FROM ${PYTHON_IMAGE} AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/opt/models \
    EMBED_CACHE_DIR=/opt/vectors \
    HF_HUB_OFFLINE=1 \
    RETRIEVER=hybrid \
    LLM_BACKEND=none

# no package installer left for anyone who gets a shell in the container
RUN useradd --no-create-home --uid 10001 --user-group --shell /usr/sbin/nologin exitzero \
 && python -m pip uninstall -y pip

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/models /opt/models
COPY --from=builder /opt/vectors /opt/vectors
COPY app/ app/
COPY knowledge/ knowledge/

USER 10001
EXPOSE 8000

# --proxy-headers trusts X-Forwarded-For only from FORWARDED_ALLOW_IPS (default 127.0.0.1),
# which the rate limiter uses as the client IP behind an ingress
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header", "--no-use-colors"]
