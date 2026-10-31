# Applications

| App | What it is | Status |
|---|---|---|
| [`api/`](api/) | FastAPI service with `/health`, `/metrics` and JSON logs. Built and scanned by CI, pushed to ECR, deployed by Argo CD, monitored with Prometheus and shipped to Elasticsearch. | Done |
| [`assistant/`](assistant/) | **ExitZero**, the Stage 4 troubleshooting assistant: paste an error, get the tool, cause, fix and copyable commands from a 248-entry knowledge base ([`assistant/knowledge/`](assistant/knowledge/)). Web UI and API run locally. | In progress |

Next for `assistant/`: embedding retrieval, an evaluation set, a Dockerfile (the image must include `knowledge/`), an Argo CD Application, then Amazon Bedrock to write the answers. See the [main README](../README.md#troubleshooting-assistant-exitzero-stage-4-in-progress).
