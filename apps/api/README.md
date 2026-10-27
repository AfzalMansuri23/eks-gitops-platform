# api

Minimal FastAPI service used to exercise the CI/CD pipeline.

| Endpoint   | Purpose                         |
|------------|---------------------------------|
| `/health`  | Liveness/readiness probe target |
| `/metrics` | Prometheus exposition format    |

Logs are JSON on stdout (one object per line).

## Run locally

```bash
docker build -t api:dev .
docker run --rm -p 8000:8000 api:dev
curl.exe -s http://localhost:8000/health
```