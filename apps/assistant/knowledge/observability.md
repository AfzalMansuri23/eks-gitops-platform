# Observability

## Prometheus ignores a ServiceMonitor or PrometheusRule
Matches: `servicemonitor`, `prometheusrule`, `servicemonitorselector`, `not picked up`
Tool: Prometheus

**Cause.** kube-prometheus-stack only selects objects labelled with its own Helm release unless the NilUsesHelmValues flags are false. The ServiceMonitor's port name or namespace selector may also not match the Service.

**Fix.** Set serviceMonitorSelectorNilUsesHelmValues, ruleSelectorNilUsesHelmValues and podMonitorSelectorNilUsesHelmValues to false, or add the release label. Check the ServiceMonitor's port name matches the Service's port name.

```sh
kubectl get servicemonitor,prometheusrule -A
kubectl -n monitoring get prometheus -o jsonpath="{.items[0].spec.serviceMonitorSelector}"
```

## Prometheus scrape fails
Matches: `server returned http status`, `context deadline exceeded`
Tool: Prometheus

**Cause.** The target's /metrics endpoint is wrong, slow, protected, or not reachable from Prometheus (NetworkPolicy, wrong port).

**Fix.** Read the error on the Targets page, then curl the endpoint from inside the cluster.

```sh
kubectl run curltest -it --rm --image=curlimages/curl --restart=Never -- curl -s http://<service>.<namespace>:<port>/metrics
```

## Prometheus out of memory (high cardinality)
Matches: `head series`, `high cardinality`, `too many series`
Tool: Prometheus

**Cause.** A metric has labels with unbounded values (user IDs, request IDs, full URLs), creating millions of series.

**Fix.** Find the top series, drop or relabel the offending labels, and raise memory only after fixing the source.

```sh
promtool tsdb analyze <data-dir>
```

## Prometheus rules fail to load
Matches: `error loading rules`, `yaml: unmarshal errors`, `parse error`
Tool: Prometheus

**Cause.** A syntax error in the rule file or an invalid PromQL expression.

**Fix.** Check the file with promtool before deploying.

```sh
promtool check rules <rules.yaml>
```

## Alert is firing but nobody got notified
Matches: `alertmanager`, `notify retry canceled`, `no notification`, `receiver`
Tool: Alertmanager

**Cause.** The route tree sends the alert to a receiver with no integration, a silence or inhibition hides it, or the webhook or SMTP credentials are wrong.

**Fix.** Test which receiver the alert's labels route to, and check for silences and notification errors in the Alertmanager logs.

```sh
amtool config routes test --config.file=alertmanager.yml <label>=<value>
amtool check-config alertmanager.yml
amtool silence query
```

## Grafana dashboard from a ConfigMap does not appear
Matches: `grafana_dashboard`, `dashboard missing`, `dashboard not showing`, `sidecar`
Tool: Grafana

**Cause.** The Grafana sidecar only loads ConfigMaps that carry the grafana_dashboard label, and only from the namespaces it is told to search.

**Fix.** Add the label grafana_dashboard: "1" to the ConfigMap and set the sidecar searchNamespace to ALL, then give it a minute to reload.

```sh
kubectl get configmap -A -l grafana_dashboard=1
```

## Grafana panels show No data
Matches: `no data`, `datasource`, `grafana`
Tool: Grafana

**Cause.** Prometheus is not scraping the target, the time range is outside the data, or the panel queries a metric name that does not exist.

**Fix.** Open the Prometheus Targets page and check the target is up, widen the time range, and run the panel's query directly in Prometheus.

```sh
kubectl -n monitoring get svc | grep prometheus
```

## Grafana data source returns Bad Gateway
Matches: `bad gateway`, `data source`
Tool: Grafana

**Cause.** Grafana cannot reach the data source URL: wrong service name or port, or a NetworkPolicy blocks it.

**Fix.** Use the in-cluster service DNS name and test it from the Grafana pod.

```sh
kubectl -n monitoring exec deploy/<grafana-deployment> -- wget -qO- http://<prometheus-service>.<namespace>:9090/-/ready
```

## Loki rejects logs
Matches: `entry out of order`, `too far behind`, `ingestion rate limit exceeded`, `per stream rate limit`
Tool: Loki

**Cause.** The client sends logs faster than the tenant's limits allow, or sends old or out-of-order timestamps for a stream.

**Fix.** Raise ingestion limits in limits_config, reduce label cardinality so streams are smaller, and check client clocks.

```sh
kubectl -n <namespace> logs <promtail-or-agent-pod> --tail=50
```

## Elasticsearch indices turn read-only (disk watermark)
Matches: `disk watermark`, `flood stage`, `read_only_allow_delete`, `read-only allow delete`
Tool: Elasticsearch

**Cause.** Disk usage passed the flood-stage watermark, so Elasticsearch blocks writes to protect the node.

**Fix.** Free disk space or grow the volume first, then clear the block. Older versions need the block cleared by hand.

```sh
curl -k -u elastic:<password> "https://localhost:9200/_cat/allocation?v"
curl -k -u elastic:<password> -X PUT https://localhost:9200/_all/_settings -H "Content-Type: application/json" -d '{"index.blocks.read_only_allow_delete": null}'
```

## Elasticsearch cluster health is red
Matches: `status: red`, `cluster health status changed`, `unassigned`
Tool: Elasticsearch

**Cause.** At least one primary shard is unassigned: a node left, a disk is full, or shard allocation is disabled.

**Fix.** Ask Elasticsearch why the shard is unassigned and fix that reason.

```sh
curl -k -u elastic:<password> "https://localhost:9200/_cluster/allocation/explain?pretty"
curl -k -u elastic:<password> "https://localhost:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason"
```

## Elasticsearch circuit breaker tripped
Matches: `circuit_breaking_exception`, `data too large`
Tool: Elasticsearch

**Cause.** A request (often a big aggregation or bulk) would use more heap than the breaker allows.

**Fix.** Make the query smaller (fewer buckets, smaller bulk batches) or give the nodes more heap.

```sh
curl -k -u elastic:<password> "https://localhost:9200/_nodes/stats/breaker?pretty"
```

## Elasticsearch mapping conflict
Matches: `mapper_parsing_exception`, `failed to parse field`, `illegal_argument_exception`
Tool: Elasticsearch

**Cause.** A field arrived with a different type than its mapping (a string where a number was mapped), so the document is rejected.

**Fix.** Make producers send consistent types, or reindex with an explicit mapping.

```sh
curl -k -u elastic:<password> "https://localhost:9200/<index>/_mapping?pretty"
```

## Datadog agent not reporting
Matches: `datadog`, `api key invalid`, `api_key`, `datadog-agent`
Tool: Datadog

**Cause.** The API key is wrong or for another Datadog site (US1 vs EU), or the agent cannot reach the intake endpoints.

**Fix.** Read the agent status for errors, and check DD_API_KEY and DD_SITE.

```sh
sudo datadog-agent status
sudo datadog-agent diagnose
```

## OpenTelemetry Collector cannot export
Matches: `exporting failed`, `otel`, `opentelemetry`, `otlp`
Tool: OpenTelemetry

**Cause.** The exporter endpoint is wrong, TLS settings do not match (insecure vs TLS), or the backend rejects the data.

**Fix.** Read the collector logs for the exporter error and check the endpoint, port (4317 gRPC, 4318 HTTP) and TLS settings.

```sh
kubectl -n <namespace> logs deploy/<otel-collector> --tail=100
```
