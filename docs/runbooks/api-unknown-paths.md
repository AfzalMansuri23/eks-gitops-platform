# Runbook: spike of 404 responses on the API

Where to look: Kibana, Discover, data view `filebeat-*` (API logs from namespace `api`, shipped by Filebeat).

## What it means

A burst of `404` access-log lines means clients are requesting paths the API does not serve. Common causes: a broken client or integration pointing at the wrong route, a bad deployment that changed or removed a route, a scanner or bot probing the service, or a health check with a typo in its path.

The API has no 4xx alert yet, so this is found in the logs, not through Alertmanager.

## Triage in Kibana

Set the time range to the incident window, then run these KQL queries:

1. How many 404s, and since when?
   ```
   kubernetes.namespace : "api" and name : "uvicorn.access" and message : "404"
   ```
   Open the histogram: a sharp step shows when it started.
2. Which path? Click the `message` field in the sidebar, or search a suspected path:
   ```
   name : "uvicorn.access" and message : "does-not-exist"
   ```
3. Which client? The access line starts with the source address, `10.244.x.x:port - "GET /path HTTP/1.1" 404`. A single address points at one misbehaving client or pod; many addresses point at a change on the server side.
4. Which pod? Add `kubernetes.pod.name` as a column. If only one pod returns 404, suspect that pod (stale image or config); if both do, suspect the route or the client.
5. Did it follow a deployment? Compare the start time with the Argo CD history for the `api` application and the last CI run.
   ```
   kubectl -n argocd get application api
   ```

## Fix

- Broken client or wrong path in a probe: correct the path in the client or the manifest (probes use `/health`).
- Route removed or renamed by a release: revert the commit on `main`; Argo CD rolls the cluster back.
- Scanner or bot: nothing to fix on the service; consider rate limiting or blocking at the Ingress.

## Verify

- The 404 histogram goes flat after the fix.
- `kubectl -n api get pods` shows both pods ready, and the Grafana "API overview" dashboard shows a normal 5xx rate.

## Drill record (2026-10-29)

Sent 160 requests for `/does-not-exist` and 160 for `/health` from a throwaway pod. Both API pods logged the 404s (82 and 78 lines). Filebeat shipped them as structured fields (`levelname`, `name`, `message` and the Kubernetes metadata), and they were found in Kibana with the queries above. Note that `message` is analysed text: use a quoted phrase such as `"does-not-exist"`, not a wildcard like `*does-not-exist*`, and join conditions with `and`.
