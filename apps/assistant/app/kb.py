"""Knowledge base: this project's own incidents plus the runbooks in knowledge/*.md.

INCIDENTS are real failures from building this platform (README troubleshooting
table, the Platform API runbooks, live debugging). The runbooks are general troubleshooting
entries for common tools. Matching is keyword scoring for now; embedding search
replaces `search` later without touching the API.
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    title: str
    source: str
    tool: str
    keywords: tuple[str, ...]
    cause: str
    fix: str
    commands: tuple[str, ...] = ()


INCIDENTS = [
    # GitHub Actions, Docker, Trivy
    Entry(
        title="OIDC role cannot be assumed from GitHub Actions",
        source="README troubleshooting · CI/CD",
        tool="GitHub Actions",
        keywords=("assumerolewithwebidentity", "not authorized to perform sts", "web identity", "oidc"),
        cause="The repo uses immutable OIDC subject claims, so a trust policy written with the plain repo name never matches the token.",
        fix="Read the subject format GitHub actually issues, put that immutable prefix in the role's trust policy sub condition, apply it, and confirm the live role has the change.",
        commands=("gh api repos/OWNER/REPO/actions/oidc/customization/sub",),
    ),
    Entry(
        title="Trivy fails the build on HIGH CVEs",
        source="README troubleshooting · CI/CD",
        tool="Trivy",
        keywords=("trivy", "cve-20", "vulnerabilit"),
        cause="A pinned dependency pulled in a vulnerable transitive package (here starlette, through an old FastAPI).",
        fix="Bump the parent packages together (FastAPI and the metrics instrumentator) so the fixed version can resolve, rebuild, and run the scan again.",
        commands=("trivy image --severity HIGH,CRITICAL <image>",),
    ),
    Entry(
        title="Image pulls from Docker Hub reset on a home connection",
        source="README troubleshooting · Docker",
        tool="Docker",
        keywords=("registry-1.docker.io", "connection reset by peer", "docker hub", "production.cloudfront.docker.com", "unexpected eof"),
        cause="The ISP's IPv6 route to Docker Hub's CDN resets or cuts long downloads (seen as EOF or connection reset), which also breaks Docker Desktop's built-in Kubernetes.",
        fix="Prefer IPv4, add a registry mirror (mirror.gcr.io) with max-concurrent-downloads 1 in the Docker Engine settings, or pull from mirror.gcr.io or public.ecr.aws directly. On kind, pull on the host and load the image into the nodes.",
        commands=("netsh interface ipv6 set prefixpolicy ::ffff:0:0/96 60 4", "docker pull mirror.gcr.io/library/<image>:<tag>", "kind load docker-image <image>:<tag> --name <cluster>"),
    ),
    # ECR
    Entry(
        title="ECR rejects a push because the tag already exists",
        source="README · CI/CD",
        tool="ECR",
        keywords=("cannot be overwritten", "repository is immutable", "tag invalid"),
        cause="The ECR repository has immutable tags, so an existing tag can never be pushed again.",
        fix="Never reuse a tag. Tag images and chart versions with the git SHA (for example 0.1.0-<sha>) so every push is unique.",
        commands=("aws ecr describe-images --repository-name <repo> --query 'imageDetails[].imageTags'",),
    ),
    # Helm
    Entry(
        title="helm upgrade fails: field is immutable",
        source="README troubleshooting · Helm",
        tool="Helm",
        keywords=("field is immutable", "spec.selector"),
        cause="The Deployment's selector labels changed between releases, and Kubernetes does not allow that on an existing Deployment.",
        fix="Keep selector labels to stable values only. If it already happened, delete the Deployment and let Helm recreate it.",
        commands=("kubectl delete deployment <name> -n <namespace>", "helm upgrade <release> <chart> -n <namespace>"),
    ),
    Entry(
        title="Helm values rejected by the chart schema (boolean, want string)",
        source="README troubleshooting · Helm",
        tool="Helm",
        keywords=("expected: string, given: boolean", "don't meet the specifications of the schema", "yaml 1.1"),
        cause="YAML 1.1 reads on, off, yes and no as booleans, so an env value of off becomes false and the schema rejects it.",
        fix='Quote the value ("off"). The chart schema already requires env values to be strings, which is what caught it.',
        commands=("helm lint --strict", "helm template <release> <chart> -f <values.yaml>"),
    ),
    # Terraform
    Entry(
        title="Terraform lock file rejects the provider in CI",
        source="README troubleshooting · Terraform",
        tool="Terraform",
        keywords=("checksums recorded", "does not match any of the checksums", "lock file", ".terraform.lock.hcl"),
        cause="The lock file only holds hashes for the platform it was created on, and CI runs on Linux.",
        fix="Lock both platforms, then commit the updated .terraform.lock.hcl.",
        commands=("terraform providers lock -platform=windows_amd64 -platform=linux_amd64",),
    ),
    Entry(
        title="Provider download resets against the Terraform registry",
        source="README troubleshooting · Terraform",
        tool="Terraform",
        keywords=("registry.terraform.io", "releases.hashicorp.com", "connection reset by peer", "wsarecv", "forcibly closed", "tls handshake timeout", "failed to install provider"),
        cause="The IPv6 route to the registry or to releases.hashicorp.com drops the connection mid-download (on Windows: wsarecv, connection forcibly closed). A mobile hotspot often works because it is IPv4 only.",
        fix="Download the provider zip over IPv4, check its SHA256, and point terraform init at a local mirror or plugin dir.",
        commands=("terraform init -plugin-dir=<path-to-providers>",),
    ),
    Entry(
        title="Terraform state is locked",
        source="Study notes · Terraform",
        tool="Terraform",
        keywords=("error acquiring the state lock", "lockid", "conditional request failed"),
        cause="Another run holds the lock, or an earlier run was killed before releasing it.",
        fix="Confirm nobody is running apply, then release the lock with the ID from the error.",
        commands=("terraform force-unlock <LockID>",),
    ),
    # AWS
    Entry(
        title="Bedrock returns ValidationException: Operation not allowed",
        source="Incident · Bedrock access",
        tool="AWS Bedrock",
        keywords=("operation not allowed", "bedrock", "not_authorized"),
        cause="An account-level block, not IAM: it fails for the root user and admins alike, and the availability check shows NOT_AUTHORIZED for every model.",
        fix="Rule out IAM with the policy simulator, then open an AWS Support case (Account and billing) asking for Bedrock invocation to be enabled.",
        commands=(
            "aws bedrock get-foundation-model-availability --model-id amazon.titan-embed-text-v2:0 --region <region>",
        ),
    ),
    # Kubernetes
    Entry(
        title="Pod stuck in ImagePullBackOff, manifest unknown",
        source="README troubleshooting · Logging",
        tool="Kubernetes",
        keywords=("manifest unknown", "back-off pulling image", "manifest for"),
        cause="The image tag was never published, so the registry has nothing to serve.",
        fix="Check the tag exists before applying, and pin the newest tag that does.",
        commands=("docker manifest inspect <image>",),
    ),
    Entry(
        title="Pod cannot get its image on kind (ErrImageNeverPull)",
        source="Runbook · Platform API",
        tool="Kubernetes",
        keywords=("errimageneverpull", "kind load", "imagepullpolicy: never"),
        cause="The Deployment uses imagePullPolicy Never and the image was never loaded into the kind node, or the node cannot reach the registry.",
        fix="Rebuild the image and load it into the cluster. For an unreachable registry, pull locally and use kind load image-archive.",
        commands=("docker build -t api:local apps/api", "kind load docker-image api:local --name lab"),
    ),
    Entry(
        title="Pod killed by out of memory (OOMKilled)",
        source="Runbook · Platform API",
        tool="Kubernetes",
        keywords=("oomkilled", "exit code 137", "out of memory"),
        cause="The container went over its memory limit (the API's limit is 128Mi) and the kernel killed it.",
        fix="Confirm Last State: OOMKilled, then raise the limit in the manifest through Git, or fix the leak. Do not edit the cluster by hand.",
        commands=("kubectl describe pod <pod> -n <namespace>", "kubectl top pod -n <namespace>"),
    ),
    Entry(
        title="Readiness probe failing",
        source="Runbook · Platform API",
        tool="Kubernetes",
        keywords=("readiness probe failed", "liveness probe failed", "probe failed"),
        cause="The probe path or port is wrong, or the app is still starting. Slow starters such as Elasticsearch and Filebeat can take a minute or more.",
        fix="Check the probe path (the API uses /health) and the logs. If the app is just slow, give it time before treating it as an outage.",
        commands=("kubectl describe pod <pod> -n <namespace>", "kubectl logs <pod> -n <namespace> --previous"),
    ),
    Entry(
        title="HTTPS shows Kubernetes Ingress Controller Fake Certificate",
        source="README troubleshooting · Kubernetes",
        tool="Kubernetes",
        keywords=("fake certificate", "ingress controller fake"),
        cause="The TLS Secret is missing, has the wrong name, or the host is not listed under tls.hosts.",
        fix="Check the Secret exists in the Ingress's namespace and that its name and the tls host match the Ingress.",
        commands=("kubectl get secret -n <namespace>", "kubectl describe ingress <name> -n <namespace>"),
    ),
    Entry(
        title="kubectl top says metrics not available",
        source="README troubleshooting · Kubernetes",
        tool="Kubernetes",
        keywords=("metrics not available", "metrics api not available", "kubectl top"),
        cause="metrics-server cannot verify the kubelet certificates on kind.",
        fix="Add --kubelet-insecure-tls to metrics-server. Local clusters only; keep verification on in real ones.",
        commands=(
            "kubectl -n kube-system patch deployment metrics-server --type=json -p='[{\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/args/-\",\"value\":\"--kubelet-insecure-tls\"}]'",
        ),
    ),
    Entry(
        title="kubectl cannot connect: wrong context",
        source="Incident · kubectl context",
        tool="Kubernetes",
        keywords=("unable to connect to the server", "eks.amazonaws.com"),
        cause="The default kubectl context still points at a cluster that was destroyed.",
        fix="List the contexts and switch to the live one, or pass --context on each command.",
        commands=("kubectl config get-contexts", "kubectl config use-context <name>"),
    ),
    # Argo CD
    Entry(
        title="Argo CD cannot reach its repo server (i/o timeout)",
        source="README troubleshooting · Kubernetes/Argo",
        tool="Argo CD",
        keywords=("argocd", "argo cd", "repo-server", "i/o timeout", "dial tcp"),
        cause="The chart's NetworkPolicies are enforced by the CNI and block the application controller from the repo server.",
        fix="Install the chart with networkPolicy.create=false (or add allow rules), then restart the Argo CD pods and hard refresh the app. Keep the policies on in real clusters.",
        commands=("kubectl -n argocd get networkpolicy", "kubectl -n argocd rollout restart deployment"),
    ),
    Entry(
        title="Argo CD app stays OutOfSync after a failed sync",
        source="README troubleshooting · Argo CD",
        tool="Argo CD",
        keywords=("outofsync", "one or more objects failed to apply", "sync operation"),
        cause="Auto-sync does not retry a commit whose last sync failed.",
        fix="Fix the cause, then trigger a sync by hand.",
        commands=("kubectl -n argocd patch application <app> --type merge -p '{\"operation\":{\"sync\":{}}}'",),
    ),
    Entry(
        title="Argo CD shows DNS errors after Docker restarts",
        source="Incident · Argo CD on kind",
        tool="Argo CD",
        keywords=("no such host", "temporary failure in name resolution", "lookup github.com"),
        cause="Cluster DNS was not ready yet after Docker Desktop restarted.",
        fix="Wait until the CoreDNS pods are Ready, then hard refresh the Argo CD application.",
        commands=("kubectl -n kube-system get pods -l k8s-app=kube-dns",),
    ),
    # Prometheus and Grafana
    # Logging: Filebeat, Elasticsearch, Kibana, ECK
    Entry(
        title="Filebeat runs but ships nothing",
        source="Runbook · Platform API",
        tool="Filebeat",
        keywords=("filebeat", "harvester", "container input", "back-off restarting failed container"),
        cause="Filebeat 9 removed the container input, so the old config starts no harvesters.",
        fix="Use a filestream input with the container and ndjson parsers, with prospector.scanner.symlinks set to true.",
        commands=("kubectl -n logging logs ds/filebeat-beat-filebeat --tail=50",),
    ),
    Entry(
        title="ECK refuses to downgrade the Elastic Stack version",
        source="README troubleshooting · Logging",
        tool="ECK",
        keywords=("downgrade", "admission webhook", "elasticsearch.k8s.elastic.co"),
        cause="The ECK admission webhook blocks version downgrades on existing Elasticsearch, Kibana and Beat resources.",
        fix="Delete and recreate the custom resources at the lower version, then trigger a prune sync if Argo CD did not retry.",
        commands=(
            "kubectl -n logging delete elasticsearch logging",
            "kubectl -n logging delete kibana logging",
            "kubectl -n logging delete beat filebeat",
        ),
    ),
    Entry(
        title="Elasticsearch health is yellow on a single node",
        source="README troubleshooting · Logging",
        tool="Elasticsearch",
        keywords=("yellow", "unassigned shards", "number_of_replicas"),
        cause="Replica shards need a second node to live on, so they stay unassigned.",
        fix="Expected on one node. To get green, set number_of_replicas to 0 on the indices (port-forward the Elasticsearch service first).",
        commands=(
            "kubectl -n logging port-forward svc/logging-es-http 9200",
            "curl -k -u elastic:<password> -X PUT https://localhost:9200/filebeat-*/_settings -H \"Content-Type: application/json\" -d '{\"index\":{\"number_of_replicas\":0}}'",
        ),
    ),
    Entry(
        title="Elasticsearch fails on vm.max_map_count too low",
        source="Incident · ELK on kind",
        tool="Elasticsearch",
        keywords=("vm.max_map_count", "max virtual memory areas"),
        cause="Elasticsearch memory-maps its indices and the node's vm.max_map_count is below 262144.",
        fix="On a real node, raise the sysctl. On kind, set node.store.allow_mmap to false instead (local only).",
        commands=("sysctl -w vm.max_map_count=262144",),
    ),
    Entry(
        title="Kibana says the server is not ready yet",
        source="Incident · ELK on kind",
        tool="Kibana",
        keywords=("kibana server is not ready yet", "elasticsearch is not ready yet", "unable to retrieve version information from elasticsearch"),
        cause="Kibana cannot reach Elasticsearch yet, either because Elasticsearch is still starting or its health is red. Elasticsearch needs about a minute to pass its readiness probe.",
        fix="Check Elasticsearch first. Kibana recovers on its own once Elasticsearch answers.",
        commands=("kubectl -n logging get elasticsearch,kibana", "kubectl -n logging logs deploy/logging-kb --tail=50"),
    ),
    Entry(
        title="Kibana query returns nothing (KQL wildcard on text)",
        source="Runbook · Platform API",
        tool="Kibana",
        keywords=("kql", "no results match", "discover"),
        cause="The message field is analysed text, so a wildcard such as *does-not-exist* does not match, and conditions need an explicit and.",
        fix='Search a quoted phrase and join conditions with and.',
        commands=('kubernetes.namespace : "api" and message : "404"',),
    ),
    # From the study notes (course labs: Kubernetes lessons and Terraform T1-T7)
    Entry(
        title="kind load docker-image fails: content digest not found",
        source="Study notes · Kubernetes lesson 6",
        tool="Kubernetes",
        keywords=("content digest", "kind load docker-image", "image-archive"),
        cause="The image is multi-platform and Docker's containerd store holds only the amd64 layers, so kind cannot export the full image.",
        fix="Save a single-platform archive and load that instead.",
        commands=(
            "docker save --platform linux/amd64 -o image.tar <image>:<tag>",
            "kind load image-archive image.tar --name <cluster>",
            "docker exec <cluster>-worker crictl images",
        ),
    ),
    Entry(
        title="Ingress path returns 404 from the app",
        source="Study notes · Kubernetes lesson 7",
        tool="Kubernetes",
        keywords=("rewrite-target", "path routing", "ingress path 404", "upstream-default-backend"),
        cause="Path routing passes the full path to the app, so /shop reaches the pod as /shop and the app has no such page. The controller log shows the request did reach the pod. A path that matches nothing goes to upstream-default-backend instead.",
        fix="Add the rewrite-target annotation with a capture group so the pod receives /, and use (/|$) in the path regex so /app does not also match /application.",
        commands=(
            "kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail=50",
            "kubectl annotate ingress <ingress> -n <namespace> nginx.ingress.kubernetes.io/rewrite-target=/$2 --overwrite",
        ),
    ),
    Entry(
        title="HPA stuck at maxReplicas (ScalingLimited TooManyReplicas)",
        source="Study notes · Kubernetes lesson 10",
        tool="Kubernetes",
        keywords=("scalinglimited", "toomanyreplicas", "desired replica count is more than the maximum"),
        cause="The HPA wants more pods than maxReplicas allows, so CPU stays above target. Scale-up is also limited per 15 seconds by the scaling policy, and scale-down waits for the stabilization window.",
        fix="Raise maxReplicas if the cluster has room, or make each pod handle more load. Expect scale-down to lag on purpose.",
        commands=("kubectl describe hpa <hpa> -n <namespace>", "kubectl get hpa -n <namespace> -w"),
    ),
    Entry(
        title="Helm values set with --set disappear after upgrade",
        source="Study notes · Helm lesson 13",
        tool="Helm",
        keywords=("--set", "values lost", "reuse-values", "value disappeared"),
        cause="helm upgrade builds values from the chart defaults plus what you pass this time. Values given with --set on an earlier install are not remembered.",
        fix="Keep every value in a values file under Git and pass it on each upgrade. Avoid --reuse-values, which also keeps stale values when the chart changes.",
        commands=("helm get values <release> -n <namespace>", "helm upgrade <release> <chart> -n <namespace> -f values.yaml"),
    ),
    Entry(
        title="Helm renders a missing value as empty with no error",
        source="Study notes · Helm lesson 14",
        tool="Helm",
        keywords=("<no value>", "renders empty", "value is empty"),
        cause="Helm templates turn a value that is not set (often a typo in the key) into an empty string instead of failing.",
        fix="Guard values that must be set with required, so the render fails loudly, and render locally before installing.",
        commands=("helm template <release> <chart> -f values.yaml --debug",),
    ),
    Entry(
        title="Terraform keeps resetting replicas changed by kubectl or an HPA",
        source="Study notes · Terraform T2",
        tool="Terraform",
        keywords=("ignore_changes", "keeps reverting", "replicas = \"4\" -> \"2\""),
        cause="The code still says the old replica count, so every apply puts it back (the plan shows replicas \"4\" -> \"2\"). State keeps the live value.",
        fix="Let one owner decide. If an HPA or people scale it, add lifecycle ignore_changes for replicas.",
        commands=("terraform plan",),
    ),
    Entry(
        title="Removing one item from a count list recreates the others",
        source="Study notes · Terraform T2",
        tool="Terraform",
        keywords=("count.index", "removing an item", "count list"),
        cause="count tracks resources by position, so removing the middle item shifts every later index and Terraform replaces them.",
        fix="Use for_each with stable keys. Move existing resources with moved blocks so nothing is recreated.",
        commands=("terraform state list", "terraform plan"),
    ),
    Entry(
        title="Refactor applied creates before slow deletes finished",
        source="Study notes · Terraform T3",
        tool="Terraform",
        keywords=("object is being deleted", "has moved to", "unexpected destroy"),
        cause="A refactor (module blocks to for_each) changed every address, so the plan destroyed and recreated everything. Creates ran in parallel with slow deletes (namespaces) and failed with already exists, leaving empty state.",
        fix="Treat an unexpected destroy in a plan as a stop sign. Add moved blocks so the plan shows has moved to and 0 to destroy.",
        commands=("terraform plan", "terraform state list"),
    ),
    Entry(
        title="terraform init fails offline: Failed to query available provider packages",
        source="Study notes · Terraform T3",
        tool="Terraform",
        keywords=("failed to query available provider packages", "plugin_cache_dir", "plugin-dir"),
        cause="init still asks the registry for the version list. The lock file pins the version and the plugin cache only saves the download, so neither works without the network.",
        fix="Point init at a folder that already holds the provider.",
        commands=("terraform init -plugin-dir=<path-to-.terraform/providers>",),
    ),
    Entry(
        title="EKS node group rejected: required service principals not found",
        source="Study notes · Terraform T6",
        tool="Amazon EKS",
        keywords=("following required service principals", "trust relationships of noderole"),
        cause="The node role was given the cluster's trust policy (eks.amazonaws.com). Worker nodes need a role that EC2 can assume.",
        fix="Set the node role trust policy to ec2.amazonaws.com, keep eks.amazonaws.com for the cluster role, and apply again.",
        commands=("aws iam get-role --role-name <node-role> --query Role.AssumeRolePolicyDocument",),
    ),
    Entry(
        title="Subnet has no internet although the route table is correct",
        source="Study notes · Terraform T5",
        tool="AWS",
        keywords=("route table association", "main route table", "aws_route_table_association"),
        cause="A route table with no subnet association does nothing. The subnets keep using the VPC's main route table, which has no route out.",
        fix="Associate the route table with each subnet.",
        commands=("aws ec2 describe-route-tables --filters Name=association.subnet-id,Values=<subnet-id>",),
    ),
    Entry(
        title="terraform import: Cannot import non-existent remote object",
        source="Study notes · Terraform T7",
        tool="Terraform",
        keywords=("cannot import non-existent remote object",),
        cause="The resource does not exist where the provider looks: it was not created yet, the ID is wrong, or you are in another region, account or workspace.",
        fix="Check the resource exists with the CLI from the same profile and region, select the right workspace, then import again.",
        commands=("terraform workspace show", "aws sts get-caller-identity"),
    ),
    Entry(
        title="New workspace plans to create everything again",
        source="Study notes · Terraform T7",
        tool="Terraform",
        keywords=("terraform workspace", "env:/"),
        cause="Each workspace has its own state. In the S3 backend, non-default workspaces live under env:/<workspace>/<key>, so a new workspace starts empty.",
        fix="Check which workspace is selected before planning. Switch back if you meant the existing one.",
        commands=("terraform workspace list", "terraform workspace select <name>"),
    ),
    Entry(
        title="curl in PowerShell fails with parameter errors",
        source="Study notes · Kubernetes lesson 7",
        tool="Windows",
        keywords=("invoke-webrequest", "a parameter cannot be found that matches parameter name"),
        cause="In Windows PowerShell, curl is an alias for Invoke-WebRequest, which takes different options.",
        fix="Call the real curl as curl.exe.",
        commands=("curl.exe -v http://<host>/",),
    ),
]


KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def _field(body: str, start: str, end: str) -> str:
    m = re.search(re.escape(start) + r"(.*?)(?=" + end + r"|\Z)", body, flags=re.S)
    return " ".join(m.group(1).split()) if m else ""


def _parse(path: Path) -> list[Entry]:
    text = path.read_text(encoding="utf-8")
    heading = re.search(r"^# (.+)$", text, flags=re.M)
    file_tool = heading.group(1).strip() if heading else path.stem
    entries = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        title, _, body = block.partition("\n")
        matches = re.search(r"^Matches:(.*)$", body, flags=re.M)
        keywords = tuple(k.strip().lower() for k in re.findall(r"`([^`]+)`", matches.group(1))) if matches else ()
        if not keywords:
            continue
        tool = re.search(r"^Tool:\s*(.+)$", body, flags=re.M)
        body = re.sub(r"^(Matches|Tool):.*$", "", body, flags=re.M)
        code = re.search(r"```sh\n(.*?)```", body, flags=re.S)
        commands = tuple(
            line.strip() for line in (code.group(1).splitlines() if code else []) if line.strip() and not line.strip().startswith("#")
        )
        entries.append(
            Entry(
                title=title.strip(),
                source=f"Runbook · {file_tool}",
                tool=tool.group(1).strip() if tool else file_tool,
                keywords=keywords,
                cause=_field(body, "**Cause.**", r"\*\*Fix\.\*\*"),
                fix=_field(body, "**Fix.**", "```"),
                commands=commands,
            )
        )
    return entries


def load_runbooks(directory: Path = KNOWLEDGE_DIR) -> list[Entry]:
    entries = []
    for path in sorted(directory.glob("*.md")):
        entries.extend(_parse(path))
    return entries


# incidents first, so they win exact ties against general runbooks
ENTRIES = INCIDENTS + load_runbooks()


def tools() -> list[str]:
    return sorted({e.tool for e in ENTRIES})


def search(text: str, limit: int = 2) -> list[Entry]:
    haystack = text.lower()
    scored = []
    for entry in ENTRIES:
        hits = [kw for kw in entry.keywords if kw in haystack]
        if hits:
            # more matched phrases, then longer (more specific) ones, then the
            # entry whose own keywords are most fully covered
            score = (len(hits), sum(len(h) for h in hits), len(hits) / len(entry.keywords))
            scored.append((score, entry))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:limit]]
