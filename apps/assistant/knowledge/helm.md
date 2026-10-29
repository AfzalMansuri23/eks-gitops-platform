# Helm

## Another operation is in progress
Matches: `another operation (install/upgrade/rollback) is in progress`, `pending-upgrade`, `pending-install`

**Cause.** An earlier helm command was killed or timed out, leaving the release stuck in a pending state.

**Fix.** Check the release history and roll back to the last deployed revision.

```sh
helm history <release> -n <namespace>
helm rollback <release> <revision> -n <namespace>
```

## Cannot re-use a name that is still in use
Matches: `cannot re-use a name that is still in use`

**Cause.** A release with that name already exists, maybe in a failed or uninstalled-but-kept state.

**Fix.** Upgrade the existing release instead, or uninstall it first.

```sh
helm list -A --all
helm upgrade --install <release> <chart> -n <namespace>
helm uninstall <release> -n <namespace>
```

## Existing resource not owned by the release
Matches: `invalid ownership metadata`, `exists and cannot be imported into the current release`, `meta.helm.sh/release-name`

**Cause.** The object already exists in the cluster but was not created by this release (made by hand or by another release).

**Fix.** Delete it, or adopt it by adding Helm's ownership label and annotations.

```sh
kubectl label <kind> <name> -n <namespace> app.kubernetes.io/managed-by=Helm
kubectl annotate <kind> <name> -n <namespace> meta.helm.sh/release-name=<release> meta.helm.sh/release-namespace=<namespace>
```

## UPGRADE FAILED: has no deployed releases
Matches: `has no deployed releases`

**Cause.** Every revision of the release failed, so there is nothing to upgrade from.

**Fix.** Uninstall and install again, or roll back to a revision that deployed if one exists.

```sh
helm history <release> -n <namespace>
helm uninstall <release> -n <namespace>
```

## Template rendering error
Matches: `error converting yaml to json`, `parse error`, `nil pointer evaluating`, `executing "`

**Cause.** The template produced invalid YAML (often indentation from nindent), or it reads a value that is not set.

**Fix.** Render locally with debug to see the broken output, and use default or required for values that may be missing.

```sh
helm template <release> <chart> -f <values.yaml> --debug
helm lint <chart> --strict
```

## Chart not found in repository
Matches: `no chart version found`, `failed to download`

**Cause.** The repo index is out of date, the chart name or version is wrong, or the repo was never added.

**Fix.** Update the repos and search for the exact versions available.

```sh
helm repo update
helm search repo <chart> --versions
```

## OCI registry: unauthorized
Matches: `oci://`, `unauthorized: authentication required`, `helm registry login`

**Cause.** Helm is not logged in to the OCI registry, or the token expired (ECR tokens last 12 hours).

**Fix.** Log in to the registry before pushing or pulling charts.

```sh
helm registry login <registry>
aws ecr get-login-password --region <region> | helm registry login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
```

## CRDs not updated on upgrade
Matches: `crds/`

**Cause.** Helm installs CRDs from the crds/ folder on first install only and never upgrades them.

**Fix.** Apply the new CRDs yourself before upgrading the chart, as the chart's upgrade notes describe.

```sh
kubectl apply --server-side -f <crds.yaml>
helm upgrade <release> <chart> -n <namespace>
```
