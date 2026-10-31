# Platform services

## Vault is sealed
Matches: `vault is sealed`, `sealed: true`
Tool: Vault

**Cause.** Vault restarted and has not been unsealed, or auto-unseal cannot reach its KMS.

**Fix.** Check the status. Unseal with the key shares, or fix access to the auto-unseal key.

```sh
vault status
vault operator unseal
```

## Vault: permission denied
Matches: `code: 403. errors:`
Tool: Vault

**Cause.** The token's policies do not allow that path and capability, or the token expired.

**Fix.** Look up the token's policies and read the policy to see which paths it covers.

```sh
vault token lookup
vault policy read <policy>
```

## Kafka consumer lag keeps growing
Matches: `consumer lag`, `kafka-consumer-groups`
Tool: Kafka

**Cause.** Consumers process messages slower than they arrive, a consumer is stuck, or there are fewer consumers than partitions.

**Fix.** Check lag per partition, then scale consumers (up to the partition count) or speed up processing.

```sh
kafka-consumer-groups.sh --bootstrap-server <broker:9092> --describe --group <group>
```

## Kafka: leader not available
Matches: `leader_not_available`, `notleaderforpartition`, `not_leader_or_follower`
Tool: Kafka

**Cause.** A broker went down and leadership is moving, or the topic was just created and has no leader yet.

**Fix.** Check the topic's partitions and in-sync replicas, and bring the missing broker back.

```sh
kafka-topics.sh --bootstrap-server <broker:9092> --describe --topic <topic>
```

## Kafka: record too large
Matches: `record_too_large`, `recordtoolargeexception`, `message_too_large`
Tool: Kafka

**Cause.** The message is bigger than the producer's max.request.size or the topic's max.message.bytes.

**Fix.** Shrink the payload (compress, store large blobs elsewhere), or raise both limits together.

```sh
kafka-configs.sh --bootstrap-server <broker:9092> --entity-type topics --entity-name <topic> --describe
```

## Istio: upstream connect error or 503
Matches: `upstream connect error or disconnect/reset before headers`, `no healthy upstream`, `503 uc`, `503 uf`
Tool: Istio

**Cause.** Envoy could not connect to a healthy upstream: pods not ready, a DestinationRule TLS mode mismatch, or ports not named for their protocol.

**Fix.** Run istioctl analyze, check sidecar sync, and check the DestinationRule's TLS settings match the PeerAuthentication.

```sh
istioctl analyze -n <namespace>
istioctl proxy-status
```

## Istio: sidecar not injected
Matches: `sidecar not injected`, `istio-injection`, `istio-proxy`
Tool: Istio

**Cause.** The namespace is not labelled for injection, or the pods were created before the label was added.

**Fix.** Label the namespace and restart the workloads.

```sh
kubectl label namespace <namespace> istio-injection=enabled --overwrite
kubectl rollout restart deploy -n <namespace>
```

## Istio: strict mTLS breaks a client outside the mesh
Matches: `peerauthentication`, `strict mtls`
Tool: Istio

**Cause.** PeerAuthentication is STRICT, so plain-text clients without a sidecar are rejected.

**Fix.** Add the client to the mesh, or use PERMISSIVE mode on that workload while you migrate.

```sh
kubectl get peerauthentication -A
```
