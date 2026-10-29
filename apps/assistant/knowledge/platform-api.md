# Platform API

These are the alert runbooks for this repo's own API (namespace `api` on the kind cluster), with the failure drills that verified them. The general runbooks sit in the other files in this folder.

## ApiTargetDown or ApiNoTargets alert is firing
Matches: `apitargetdown`, `apinotargets`, `target down`, `api down`
Tool: Prometheus

**Cause.** ApiTargetDown: Prometheus has an `api` target but cannot scrape it for more than 1 minute, so a pod is crashing, not ready or unreachable. ApiNoTargets: Prometheus has no `api` target at all for more than 2 minutes, so the Deployment is scaled to 0 or deleted, or the ServiceMonitor is gone. Both alerts need the problem to last before they fire, so an outage is usually visible 2 to 3 minutes after it starts.

**Fix.** Check Argo CD first, then the replicas and pods. If replicas were changed by hand, Argo restores them within seconds while auto-sync is on; if auto-sync was paused, re-apply `argocd/applications/api.yaml`. For a bad change in Git, revert the commit on `main` and let Argo roll the cluster back; do not fix it by editing the cluster. If the image is missing on kind, rebuild and load it.

```sh
kubectl -n argocd get application api
kubectl -n api get deploy api
kubectl -n api get pods
kubectl -n api describe pod <pod>
kubectl -n api logs <pod> --previous
kubectl -n api get deploy,svc,servicemonitor
```

**Triage.**

1. Is Argo CD healthy and in sync? `OutOfSync` or a paused sync means someone changed the cluster or turned off auto-sync.
2. How many replicas are there?
3. If pods exist but are not ready or are restarting, describe them and read the previous logs. Logs are JSON. Common causes: image not present on the node (`ErrImageNeverPull` on kind), a failing readiness probe on `/health`, out of memory (the limit is 128Mi).
4. If there are no pods at all, check that the Deployment and the ServiceMonitor still exist.

Rebuild and load the image on kind:

```sh
docker build -t api:local apps/api
kind load docker-image api:local --name lab
```

**Verify.** `kubectl -n api get deploy api` shows `2/2` ready. In Prometheus the `api` targets are `up` and the alert goes back to inactive (about 1 minute after recovery). The Grafana "API overview" dashboard shows "Pods up = 2".

**Drill record (2026-10-28).** Scaled the Deployment to 0 with auto-sync paused. `ApiNoTargets` went pending after about 1 minute and fired after about 3 minutes. Re-applying the Application restored 2 ready pods in 11 seconds, and the alert resolved after about 50 seconds. With auto-sync on, the same manual scale-down was reverted in under 5 seconds and no alert fired.

## Spike of 404 responses on the API
Matches: `uvicorn.access`, `404 spike`, `spike of 404`, `does-not-exist`
Tool: Kibana

**Cause.** A burst of `404` access-log lines means clients are requesting paths the API does not serve: a broken client or integration pointing at the wrong route, a bad deployment that changed or removed a route, a scanner or bot probing the service, or a health check with a typo in its path. The API has no 4xx alert yet, so this is found in the logs (Kibana, data view `filebeat-*`), not through Alertmanager.

**Fix.** For a broken client or a wrong path in a probe, correct the path in the client or the manifest (probes use `/health`). For a route removed or renamed by a release, revert the commit on `main` and Argo CD rolls the cluster back. For a scanner or bot, there is nothing to fix on the service; consider rate limiting or blocking at the Ingress.

```sh
kubectl -n argocd get application api
kubectl -n api get pods
```

**Triage in Kibana.** Set the time range to the incident window, then:

1. How many 404s, and since when? Query `kubernetes.namespace : "api" and name : "uvicorn.access" and message : "404"` and open the histogram: a sharp step shows when it started.
2. Which path? Click the `message` field in the sidebar, or search a suspected path with `name : "uvicorn.access" and message : "does-not-exist"`.
3. Which client? The access line starts with the source address, `10.244.x.x:port - "GET /path HTTP/1.1" 404`. A single address points at one misbehaving client or pod; many addresses point at a change on the server side.
4. Which pod? Add `kubernetes.pod.name` as a column. If only one pod returns 404, suspect that pod (stale image or config); if both do, suspect the route or the client.
5. Did it follow a deployment? Compare the start time with the Argo CD history for the `api` application and the last CI run.

**Verify.** The 404 histogram goes flat after the fix. `kubectl -n api get pods` shows both pods ready, and the Grafana "API overview" dashboard shows a normal 5xx rate.

**Drill record (2026-10-29).** Sent 160 requests for `/does-not-exist` and 160 for `/health` from a throwaway pod. Both API pods logged the 404s (82 and 78 lines). Filebeat shipped them as structured fields (`levelname`, `name`, `message` and the Kubernetes metadata), and they were found in Kibana with the queries above. `message` is analysed text: use a quoted phrase such as `"does-not-exist"`, not a wildcard like `*does-not-exist*`, and join conditions with `and`.
