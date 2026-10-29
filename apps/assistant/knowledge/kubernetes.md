# Kubernetes

## Pod in CrashLoopBackOff
Matches: `crashloopbackoff`, `back-off restarting failed container`

**Cause.** The container starts and exits again. CrashLoopBackOff only says Kubernetes is waiting before the next restart. The reason is in the previous container's logs: a bad command, a missing env var or Secret, an app crash on startup, or a liveness probe killing a healthy app.

**Fix.** Read the previous container's logs and the pod events, fix the cause in Git, and let the rollout replace the pod.

```sh
kubectl logs <pod> -n <namespace> --previous
kubectl describe pod <pod> -n <namespace>
```

## Image pull fails: ImagePullBackOff or ErrImagePull
Matches: `imagepullbackoff`, `errimagepull`, `pull access denied`, `repository does not exist`, `authentication required`

**Cause.** The node cannot pull the image: a typo in the image name or tag, a private registry without an imagePullSecret, a registry rate limit, or the node has no network route to the registry.

**Fix.** Check the exact image reference in the pod events, confirm it exists, and add an imagePullSecret (or node IAM permissions on a cloud registry) for private images.

```sh
kubectl describe pod <pod> -n <namespace>
kubectl create secret docker-registry regcred --docker-server=<registry> --docker-username=<user> --docker-password=<token> -n <namespace>
```

## Pod stuck in Pending (FailedScheduling)
Matches: `failedscheduling`, `insufficient cpu`, `insufficient memory`, `untolerated taint`, `didn't tolerate`, `didn't match pod's node affinity`

**Cause.** The scheduler cannot place the pod: no node has enough CPU or memory for its requests, a PersistentVolumeClaim is not bound, node affinity rules exclude every node, or a taint keeps it off the free nodes.

**Fix.** Read the FailedScheduling event, then lower the requests, add node capacity, fix the affinity rules or storage class, or add the right toleration.

```sh
kubectl describe pod <pod> -n <namespace>
kubectl get events -n <namespace> --field-selector reason=FailedScheduling
kubectl describe nodes
```

## CreateContainerConfigError: missing Secret or ConfigMap
Matches: `createcontainerconfigerror`, `secret "`, `configmap "`, `couldn't find key`

**Cause.** The pod references a Secret, ConfigMap or a key inside one that does not exist in the pod's namespace.

**Fix.** Create the missing object (or key) in the same namespace as the pod, or fix the name in the manifest. Secrets are namespaced, so one in another namespace does not count.

```sh
kubectl describe pod <pod> -n <namespace>
kubectl get secret,configmap -n <namespace>
```

## RunContainerError: executable not found
Matches: `runcontainererror`, `createcontainererror`, `executable file not found in $path`, `exec: "`

**Cause.** The command or entrypoint in the manifest does not exist in the image, or the path is wrong.

**Fix.** Check the image's real entrypoint and fix `command` or `args` in the manifest.

```sh
kubectl describe pod <pod> -n <namespace>
docker image inspect <image> --format '{{.Config.Entrypoint}} {{.Config.Cmd}}'
```

## Init container never finishes (Init:0/1)
Matches: `init:0/`, `init:crashloopbackoff`, `init:error`

**Cause.** An init container is failing or waiting forever, often for a dependency (database, DNS name, migration) that is not reachable.

**Fix.** Read the init container's own logs, fix the dependency or the check it runs.

```sh
kubectl logs <pod> -n <namespace> -c <init-container>
kubectl describe pod <pod> -n <namespace>
```

## Service has no endpoints
Matches: `no endpoints available for service`, `endpoints: <none>`, `has no endpoints`

**Cause.** The Service selector does not match the labels on any ready pod, or the matching pods are not ready.

**Fix.** Compare the Service selector with the pod labels and fix whichever is wrong. If labels match, fix the readiness probe.

```sh
kubectl get endpoints <service> -n <namespace>
kubectl describe svc <service> -n <namespace>
kubectl get pods -n <namespace> --show-labels
```

## Ingress returns 502, 503 or 404 from the default backend
Matches: `ingress-nginx`, `default backend - 404`, `503 service temporarily unavailable`, `ingress controller`

**Cause.** The ingress controller cannot reach a healthy backend: the Service has no endpoints, the service port in the Ingress is wrong, the host or path does not match, or pods are crashing.

**Fix.** Check the Ingress rules point at the right Service and port, then check the Service has endpoints and read the controller logs.

```sh
kubectl describe ingress <ingress> -n <namespace>
kubectl get endpoints <service> -n <namespace>
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller --tail=100
```

## Pods evicted for DiskPressure or memory
Matches: `evicted`, `diskpressure`, `the node was low on resource`, `memorypressure`

**Cause.** The node ran low on disk (often container logs, images or emptyDir volumes) or memory, and the kubelet evicted pods to protect itself.

**Fix.** Free space on the node, set ephemeral-storage requests and limits, rotate logs, and clean up the evicted pod records.

```sh
kubectl describe node <node>
kubectl get pods -A --field-selector=status.phase=Failed
kubectl delete pods -A --field-selector=status.phase=Failed
```

## Node is NotReady
Matches: `notready`, `kubelet stopped posting node status`, `container runtime network not ready`, `cni plugin not initialized`

**Cause.** The kubelet on that node stopped reporting: the kubelet or container runtime crashed, the CNI plugin is not running, the node is out of resources, or it lost network to the control plane.

**Fix.** Read the node conditions, then the kubelet logs on the node. Restart the kubelet or runtime, or replace the node if it is unhealthy.

```sh
kubectl describe node <node>
kubectl get pods -n kube-system -o wide
systemctl status kubelet
journalctl -u kubelet --since "15 min ago" --no-pager
```

## PersistentVolumeClaim stuck in Pending
Matches: `waiting for first consumer`, `no persistent volumes available`, `provisioningfailed`, `storageclass.storage.k8s.io`

**Cause.** No volume can be provisioned: the StorageClass does not exist or has no provisioner, the CSI driver is not installed, or the class uses WaitForFirstConsumer and no pod uses the claim yet.

**Fix.** Check the claim's events and the StorageClass. Install the CSI driver or pick an existing class. WaitForFirstConsumer is normal until a pod is scheduled.

```sh
kubectl describe pvc <claim> -n <namespace>
kubectl get storageclass
```

## Multi-Attach error for a volume
Matches: `multi-attach error`, `volume is already exclusively attached`, `already used by pod`

**Cause.** A ReadWriteOnce volume is still attached to a pod on another node, usually during a rolling update where the new pod starts before the old one stops.

**Fix.** Use the Recreate strategy for Deployments with RWO volumes (or a StatefulSet), and wait for the old pod to terminate. Only delete a stuck VolumeAttachment after confirming the old node no longer uses it.

```sh
kubectl get volumeattachment
kubectl describe pod <pod> -n <namespace>
```

## RBAC forbidden
Matches: `is forbidden: user`, `cannot list resource`, `cannot get resource`, `cannot create resource`, `cannot watch resource`

**Cause.** The user or ServiceAccount has no Role or ClusterRole granting that verb on that resource in that namespace.

**Fix.** Check exactly what is allowed, then add a Role and RoleBinding with only the verbs needed.

```sh
kubectl auth can-i <verb> <resource> -n <namespace> --as system:serviceaccount:<namespace>:<serviceaccount>
kubectl get rolebinding,clusterrolebinding -A -o wide
```

## Rollout stuck: progress deadline exceeded
Matches: `progressdeadlineexceeded`, `exceeded its progress deadline`, `waiting for deployment`

**Cause.** New pods never became ready within the deadline: a crash, a failing readiness probe, an image pull error, or not enough capacity.

**Fix.** Find why the new ReplicaSet's pods are not ready. Roll back if production is affected, then fix forward.

```sh
kubectl rollout status deploy/<deployment> -n <namespace>
kubectl get rs -n <namespace>
kubectl rollout undo deploy/<deployment> -n <namespace>
```

## Namespace stuck in Terminating
Matches: `stuck in terminating`, `namespace terminating`, `finalizers`, `some content in the namespace has finalizers remaining`

**Cause.** Objects inside still carry finalizers, often custom resources whose controller (operator) was removed first, or an API service that is unavailable.

**Fix.** List what is left in the namespace and let its controller clean it up. Remove finalizers by hand only as a last resort, since it can leave cloud resources behind.

```sh
kubectl get namespace <namespace> -o json
kubectl api-resources --verbs=list --namespaced -o name | xargs -n 1 kubectl get --show-kind --ignore-not-found -n <namespace>
kubectl get apiservice | grep False
```

## DNS does not resolve inside pods
Matches: `could not resolve host`, `temporary failure in name resolution`, `no such host`, `server misbehaving`

**Cause.** CoreDNS pods are down or overloaded, a NetworkPolicy blocks port 53, or the name is wrong (Services resolve as name.namespace.svc.cluster.local).

**Fix.** Test resolution from a throwaway pod, check CoreDNS is running, and allow UDP and TCP 53 to kube-dns in your NetworkPolicies.

```sh
kubectl run dnstest -it --rm --image=busybox:1.36 --restart=Never -- nslookup kubernetes.default
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system logs -l k8s-app=kube-dns --tail=50
```

## kubectl: certificate has expired
Matches: `x509: certificate has expired`, `certificate has expired or is not yet valid`

**Cause.** The client certificate in the kubeconfig (or the cluster's own certificates on kubeadm clusters) passed its expiry date. kubeadm certificates last one year.

**Fix.** On managed clusters, fetch fresh credentials. On kubeadm, renew the certificates and restart the control plane components.

```sh
kubeadm certs check-expiration
kubeadm certs renew all
```

## kubectl connection to localhost:8080 refused
Matches: `localhost:8080 was refused`, `did you specify the right host or port`

**Cause.** kubectl found no kubeconfig, so it fell back to localhost:8080.

**Fix.** Point KUBECONFIG at the right file or fetch credentials for the cluster.

```sh
kubectl config view
export KUBECONFIG=$HOME/.kube/config
```

## HPA shows unknown metrics
Matches: `failedgetresourcemetric`, `unable to get metrics`, `missing request for cpu`, `<unknown>/`

**Cause.** metrics-server is not installed or not working, or the pods have no CPU or memory requests, so a percentage cannot be calculated.

**Fix.** Install or fix metrics-server and set resource requests on the target pods.

```sh
kubectl describe hpa <hpa> -n <namespace>
kubectl top pods -n <namespace>
```

## Exceeded ResourceQuota
Matches: `exceeded quota`, `forbidden: exceeded quota`, `must specify limits`

**Cause.** The namespace has a ResourceQuota and this pod would go over it, or the quota requires limits that the pod does not set.

**Fix.** Check usage against the quota, then raise the quota or lower the requests. Add limits if the quota demands them.

```sh
kubectl describe resourcequota -n <namespace>
```

## Admission webhook call failed
Matches: `failed calling webhook`, `internal error occurred: failed calling webhook`

**Cause.** A validating or mutating webhook's service is down or unreachable (often after its operator was removed), so the API server rejects the request.

**Fix.** Bring the webhook's service back, or delete the webhook configuration if the operator is gone for good.

```sh
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl get endpoints -A | grep webhook
```

## Job failed: BackoffLimitExceeded
Matches: `backofflimitexceeded`, `job has reached the specified backoff limit`

**Cause.** The Job's pods failed more times than backoffLimit allows.

**Fix.** Read the logs of the failed pods, fix the cause, then delete and recreate the Job (a finished Job does not retry).

```sh
kubectl describe job <job> -n <namespace>
kubectl logs job/<job> -n <namespace>
```

## No matches for kind (CRD missing)
Matches: `no matches for kind`, `ensure crds are installed first`, `the server doesn't have a resource type`

**Cause.** The custom resource's CRD is not installed, or the manifest uses an apiVersion the cluster no longer serves.

**Fix.** Install the CRDs before the resources that use them, and update deprecated apiVersions.

```sh
kubectl get crd
kubectl api-resources | grep -i <kind>
```

## Ingress rejected: host and path already defined
Matches: `is already defined in ingress`, `validate.nginx.ingress.kubernetes.io`, `host and path combination already defined`

**Cause.** Another Ingress already owns that host and path, and the ingress-nginx admission webhook refuses a duplicate.

**Fix.** Find the Ingress that owns the host, then use a different host or path, or merge the rules into one Ingress.

```sh
kubectl get ingress -A
```

## Container exited with code 143
Matches: `exit code 143`, `exited (143)`, `sigterm`

**Cause.** The process received SIGTERM and stopped, which is normal during a rollout, a scale-down or a node drain. It is a problem only if the app was not meant to stop.

**Fix.** Check events for who stopped it. Make the app handle SIGTERM and finish in-flight work within terminationGracePeriodSeconds.

```sh
kubectl describe pod <pod> -n <namespace>
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```
