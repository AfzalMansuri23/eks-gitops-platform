# Runbook: API down or not being scraped

Alerts: `ApiTargetDown`, `ApiNoTargets` (severity: critical)

## What it means

| Alert | Meaning |
|---|---|
| `ApiTargetDown` | Prometheus has an `api` target but cannot scrape it for more than 1 minute. A pod is crashing, not ready, or unreachable. |
| `ApiNoTargets` | Prometheus has no `api` target at all for more than 2 minutes. The Deployment is scaled to 0, deleted, or the ServiceMonitor is gone. |

Both alerts need the problem to last (1 and 2 minutes) before they fire, so an outage is usually visible 2 to 3 minutes after it starts.

## Triage

1. Is Argo CD healthy and in sync?
   ```
   kubectl -n argocd get application api
   ```
   `OutOfSync` or a paused sync means someone changed the cluster or turned off auto-sync.
2. How many replicas are there?
   ```
   kubectl -n api get deploy api
   kubectl -n api get pods
   ```
3. If pods exist but are not ready or are restarting:
   ```
   kubectl -n api describe pod <pod>
   kubectl -n api logs <pod> --previous
   ```
   Logs are JSON. Common causes: image not present on the node (`ErrImageNeverPull` on kind), failing readiness probe on `/health`, out of memory (limit is 128Mi).
4. If there are no pods at all, check the ServiceMonitor and Deployment still exist:
   ```
   kubectl -n api get deploy,svc,servicemonitor
   ```

## Fix

- Replicas were changed by hand: with auto-sync on, Argo restores them within seconds. If auto-sync was paused, re-enable it by re-applying `argocd/applications/api.yaml`.
- Bad change in Git: revert the commit on `main`. Argo rolls the cluster back to the last good state. Do not fix it by editing the cluster.
- Image missing on kind: rebuild and load it.
  ```
  docker build -t api:local apps/api
  kind load docker-image api:local --name lab
  ```

## Verify

- `kubectl -n api get deploy api` shows `2/2` ready.
- In Prometheus the `api` targets are `up` and the alert goes back to inactive (about 1 minute after recovery).
- The Grafana "API overview" dashboard shows "Pods up = 2".

## Drill record (2026-10-28)

Scaled the Deployment to 0 with auto-sync paused. `ApiNoTargets` went pending after about 1 minute and fired after about 3 minutes. Re-applying the Application restored 2 ready pods in 11 seconds, and the alert resolved after about 50 seconds. With auto-sync on, the same manual scale-down was reverted in under 5 seconds and no alert fired.
