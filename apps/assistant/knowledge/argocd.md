# Argo CD

## ComparisonError: failed to load target state
Matches: `comparisonerror`, `failed to load target state`, `manifest generation error`

**Cause.** Argo CD could not render the manifests: a Helm or Kustomize error, a wrong path or revision, or the repo server cannot reach Git.

**Fix.** Hard refresh the app to see the full error, then read the repo server logs.

```sh
argocd app get <app> --hard-refresh
kubectl -n argocd logs deploy/argocd-repo-server --tail=100
```

## Repository authentication failed
Matches: `authentication required`, `repository not accessible`, `repository not found`, `ssh: handshake failed`

**Cause.** The repo is private and Argo CD has no credentials for it, or the token or SSH key expired.

**Fix.** Add or update the repository credentials.

```sh
argocd repo list
argocd repo add <repo-url> --username <user> --password <token>
```

## App goes OutOfSync again right after syncing
Matches: `keeps going outofsync`, `immediately outofsync`, `ignoredifferences`

**Cause.** A controller or webhook changes a field after Argo CD applies it, for example an HPA changing replicas or a webhook injecting a sidecar.

**Fix.** Remove the field from Git (replicas when an HPA is in charge) or add ignoreDifferences for it in the Application.

```sh
argocd app diff <app>
```

## App health is Degraded
Matches: `degraded`, `health status degraded`

**Cause.** A resource in the app is unhealthy: pods crashing, a rollout stuck, or a PVC not bound. Sync can be green while health is not.

**Fix.** Find the unhealthy resource in the app view and debug it like any Kubernetes object.

```sh
argocd app get <app>
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

## Sync waits forever on a hook
Matches: `waiting for completion of hook`, `presync`, `postsync`

**Cause.** A sync hook Job (migration, check) is hanging or retrying.

**Fix.** Read the hook Job's logs. Terminate the operation if you need to retry.

```sh
kubectl get jobs -n <namespace>
argocd app terminate-op <app>
```

## Not permitted in project
Matches: `is not permitted in project`, `not permitted to deploy`

**Cause.** The AppProject does not allow that destination namespace, cluster, source repo or resource kind.

**Fix.** Add the destination, repo or resource kind to the AppProject.

```sh
argocd proj get <project>
```

## Login fails: invalid username or password
Matches: `invalid username or password`, `argocd-initial-admin-secret`

**Cause.** The admin password is the generated one in the initial admin secret, unless someone changed it.

**Fix.** Read the initial password from the secret, then change it and delete the secret.

```sh
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
argocd account update-password
```
