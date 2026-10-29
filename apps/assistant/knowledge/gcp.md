# GCP

## Permission denied on a GCP resource
Matches: `permission_denied`, `does not have permission`, `iam_permission_denied`

**Cause.** The active account or service account lacks the IAM role for that action, the role is granted on a different project, or gcloud is using a different account than you expect.

**Fix.** Check the active account and project, then grant the narrowest predefined role on the right resource.

```sh
gcloud auth list
gcloud config get-value project
gcloud projects get-iam-policy <project> --flatten="bindings[].members" --filter="bindings.members:<member>" --format="table(bindings.role)"
```

## API has not been used or is disabled
Matches: `service_disabled`, `has not been used in project`, `it is disabled`, `api not enabled`

**Cause.** The Google API for that service is not enabled in the project.

**Fix.** Enable it, then wait a minute for it to propagate.

```sh
gcloud services enable <service>.googleapis.com
gcloud services list --enabled
```

## Quota exceeded
Matches: `quota_exceeded`, `quota exceeded`, `resource_exhausted`

**Cause.** The project hit a regional or global quota, for example CPUs, IP addresses or API requests per minute.

**Fix.** Check the quota usage in that region and request an increase, or use another region.

```sh
gcloud compute regions describe <region> --format="table(quotas.metric,quotas.limit,quotas.usage)"
```

## Zone resource pool exhausted
Matches: `zone_resource_pool_exhausted`, `does not have enough resources available`

**Cause.** Google has no spare capacity of that machine type in that zone right now.

**Fix.** Try another zone or machine type, or use regional resources that can pick a zone.

```sh
gcloud compute machine-types list --filter="zone:<zone>"
```

## Application Default Credentials not found
Matches: `could not automatically determine credentials`, `default credentials were not found`, `application default credentials`

**Cause.** Client libraries and Terraform look for Application Default Credentials, which are separate from gcloud auth login.

**Fix.** Create ADC locally, or attach a service account on GCE, GKE or Cloud Run.

```sh
gcloud auth application-default login
```

## GKE: gke-gcloud-auth-plugin not found
Matches: `gke-gcloud-auth-plugin`, `executable gke-gcloud-auth-plugin not found`

**Cause.** kubectl needs the GKE auth plugin to get tokens, and it is not installed or not on PATH.

**Fix.** Install the plugin and fetch credentials again.

```sh
gcloud components install gke-gcloud-auth-plugin
gcloud container clusters get-credentials <cluster> --region <region>
```
Tool: GKE

## GKE Workload Identity cannot get a token
Matches: `iam.serviceaccounts.getaccesstoken`, `unable to generate access token`, `workload identity`

**Cause.** The Kubernetes ServiceAccount is not annotated with the Google service account, or the Google service account has no roles/iam.workloadIdentityUser binding for that KSA.

**Fix.** Add the IAM binding and the annotation, then restart the pods.

```sh
gcloud iam service-accounts add-iam-policy-binding <gsa-email> --role roles/iam.workloadIdentityUser --member "serviceAccount:<project>.svc.id.goog[<namespace>/<ksa>]"
kubectl annotate serviceaccount <ksa> -n <namespace> iam.gke.io/gcp-service-account=<gsa-email>
```
Tool: GKE

## Artifact Registry pull or push denied
Matches: `artifactregistry.repositories.downloadartifacts`, `artifactregistry.repositories.uploadartifacts`, `docker.pkg.dev`

**Cause.** Docker is not configured to authenticate to Artifact Registry, or the identity lacks the reader or writer role on the repository.

**Fix.** Configure the Docker credential helper and grant roles/artifactregistry.reader (pull) or writer (push).

```sh
gcloud auth configure-docker <region>-docker.pkg.dev
```
Tool: Artifact Registry

## Cannot connect to Cloud SQL
Matches: `cloudsql.instances.connect`, `cloud sql`, `cloudsql`

**Cause.** The client is not authorized (no roles/cloudsql.client), private IP is not reachable from the client's VPC, or the public IP has no authorized network.

**Fix.** Connect through the Cloud SQL Auth Proxy with the right role, or fix the private networking.

```sh
gcloud sql instances describe <instance> --format="value(ipAddresses)"
```
Tool: Cloud SQL

## Organization policy blocks the action
Matches: `violates constraint`, `constraints/`, `org policy`

**Cause.** An organization policy forbids it, for example external IPs, service account key creation or resource locations.

**Fix.** Read the constraint and either change the design or ask the org admin for an exception.

```sh
gcloud resource-manager org-policies describe <constraint> --project <project>
```

## Billing not enabled
Matches: `billing account`, `billing must be enabled`, `billing_disabled`

**Cause.** The project has no active billing account, which most APIs need even within the free tier.

**Fix.** Link a billing account to the project.

```sh
gcloud billing projects describe <project>
gcloud billing projects link <project> --billing-account <billing-account-id>
```
