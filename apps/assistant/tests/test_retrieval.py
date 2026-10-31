import pytest

from app import kb
from tests.eval.run_eval import CASES, evaluate

# one real error message per tool: (message, expected tool)
REALISTIC = [
    ("kubelogin is not installed which is required to connect to AAD enabled cluster", "AKS"),
    ("An error occurred (ExpiredToken) when calling the DescribeInstances operation: The security token included in the request is expired", "AWS"),
    ("ValidationException: Operation not allowed calling bedrock InvokeModel", "AWS Bedrock"),
    ("alert is firing in Alertmanager but no notification was sent to the receiver", "Alertmanager"),
    ("InvalidParameterException: Following required service principals [eks.amazonaws.com] were not found in the trust relationships of nodeRole", "Amazon EKS"),
    ('fatal: [web1]: UNREACHABLE! => {"changed": false, "msg": "Failed to connect to the host via ssh"}', "Ansible"),
    ("rpc error: dial tcp 10.96.4.2:8081: i/o timeout argocd repo-server", "Argo CD"),
    ("denied: Permission 'artifactregistry.repositories.uploadArtifacts' denied on resource", "Artifact Registry"),
    ("(AuthorizationFailed) The client does not have authorization to perform action 'Microsoft.Compute/virtualMachines/write'", "Azure"),
    ("Cloud SQL Auth Proxy: failed to connect to instance: dial error", "Cloud SQL"),
    ("dig api.internal returns status: NXDOMAIN", "DNS"),
    ("datadog-agent status: API Key invalid, dropping transaction", "Datadog"),
    ("Back-off restarting failed container web in pod web-5c9d", "Kubernetes"),
    ("docker: Error response from daemon: Bind for 0.0.0.0:8080 failed: port is already allocated.", "Docker"),
    ("admission webhook denied: Version downgrades are not supported elasticsearch.k8s.elastic.co", "ECK"),
    ("tag invalid: The image tag '0.1.0' already exists in the repository and cannot be overwritten because the repository is immutable", "ECR"),
    ("bootstrap check failure: max virtual memory areas vm.max_map_count [65530] is too low", "Elasticsearch"),
    ("Back-off restarting failed container filebeat", "Filebeat"),
    ("ERROR: (gcloud.services.enable) PERMISSION_DENIED: Billing account for project is not found. Billing must be enabled", "GCP"),
    ("error: executable gke-gcloud-auth-plugin not found", "GKE"),
    ("! [rejected] main -> main (non-fast-forward)", "Git"),
    ("Not authorized to perform sts:AssumeRoleWithWebIdentity", "GitHub Actions"),
    ("This job is stuck because you don't have any active runners online", "GitLab CI"),
    ("Grafana panel shows No data for the datasource Prometheus", "Grafana"),
    ("Access to fetch at 'http://api.local' from origin 'http://localhost:3000' has been blocked by CORS policy", "HTTP API"),
    ("Error: UPGRADE FAILED: cannot patch deployment: field is immutable spec.selector", "Helm"),
    ("upstream connect error or disconnect/reset before headers. reset reason: connection failure", "Istio"),
    ("java.lang.OutOfMemoryError: Java heap space on the Jenkins controller", "Jenkins"),
    ("WARN Error while fetching metadata with correlation id 7 : {orders=LEADER_NOT_AVAILABLE}", "Kafka"),
    ("Kibana server is not ready yet", "Kibana"),
    ("Last State: Terminated Reason: OOMKilled Exit Code: 137", "Kubernetes"),
    ("bash: ulimit: Too many open files", "Linux"),
    ("Loki push failed: entry too far behind, ingestion rate limit exceeded", "Loki"),
    ("MongoServerSelectionError: Server selection timed out after 30000 ms", "MongoDB"),
    ("ERROR 1040 (HY000): Too many connections", "MySQL"),
    ("curl: (7) Failed to connect to 10.0.0.5 port 8080: Connection refused", "Networking"),
    ('nginx: [emerg] unknown directive "proxy_passs" in /etc/nginx/conf.d/default.conf', "Nginx"),
    ("otel collector: Exporting failed. Will retry the request after interval. error: context deadline exceeded", "OpenTelemetry"),
    ('FATAL: no pg_hba.conf entry for host "10.0.0.7", user "app"', "PostgreSQL"),
    ("ALERT ApiTargetDown firing for api", "Prometheus"),
    ("OOM command not allowed when used memory > 'maxmemory'", "Redis"),
    ("x509: certificate signed by unknown authority", "TLS"),
    ("Error: Error acquiring the state lock LockID: abc", "Terraform"),
    ("Trivy: Total: 2 (HIGH: 2) CVE-2025-1234 starlette", "Trivy"),
    ("Error: Vault is sealed", "Vault"),
    ("Invoke-WebRequest : A parameter cannot be found that matches parameter name 'X'", "Windows"),
    ("cert-manager: Certificate is not ready, order is pending, challenge pending", "cert-manager"),
]


def test_knowledge_base_loaded():
    assert len(kb.INCIDENTS) == 40
    assert len(kb.ENTRIES) >= 248
    assert len(kb.tools()) >= 46


def test_every_tool_has_a_realistic_message():
    assert {tool for _, tool in REALISTIC} == set(kb.tools())


@pytest.mark.parametrize("entry", kb.ENTRIES, ids=lambda e: e.title[:50])
def test_entry_found_by_its_first_keyword(entry, keyword):
    assert entry in [e for e, _ in keyword.search(entry.keywords[0], 5)]


@pytest.mark.parametrize("text,tool", REALISTIC, ids=[t for _, t in REALISTIC])
@pytest.mark.parametrize("name", ["keyword", "hybrid"])
def test_realistic_message_hits_right_tool(text, tool, name, request):
    hits = request.getfixturevalue(name).search(text, 1)
    assert hits and hits[0][0].tool == tool


@pytest.mark.parametrize("name", ["keyword", "embedding", "hybrid"])
@pytest.mark.parametrize("case", CASES["negative"], ids=lambda c: c["text"][:30])
def test_negative_is_not_found(case, name, request):
    assert request.getfixturevalue(name).search(case["text"], 3) == []


def test_paraphrases_share_no_matches_string():
    by_title = {e.title.lower(): e for e in kb.ENTRIES}
    for case in CASES["paraphrase"]:
        entry = next(e for t, e in by_title.items() if case["want"].lower() in t)
        text = case["text"].lower()
        assert not [kw for kw in entry.keywords if kw in text], case["text"]


def test_hybrid_beats_keyword_without_losing_exact(keyword, hybrid):
    kw, hy = evaluate(keyword), evaluate(hybrid)
    assert hy["exact"]["top1"] == kw["exact"]["top1"] == 1.0
    assert hy["paraphrase"]["top1"] >= kw["paraphrase"]["top1"] + 0.5
    assert hy["paraphrase"]["top3"] >= 0.85
    assert hy["negative"]["rejected"] == 1.0
