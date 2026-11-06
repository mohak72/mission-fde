# In-Cluster DNS Resolution Failure

## Symptoms

- Application logs show errors like `could not resolve host`, `Name or service not known`, or `DNS lookup failed` when calling another in-cluster service by name.
- Intermittent failures are common: some requests resolve fine, others time out, suggesting a capacity or flakiness issue rather than total DNS outage.
- `kubectl exec` into an affected pod and running `nslookup <service-name>` either hangs, times out, or returns `SERVFAIL`/`NXDOMAIN` for a service that genuinely exists.
- CoreDNS pods may show elevated restart counts or CPU throttling in cluster metrics.

## Likely Causes

- CoreDNS pods are overloaded (too few replicas for the cluster's query volume) or being OOMKilled/CPU-throttled.
- A `NetworkPolicy` is inadvertently blocking traffic to the `kube-dns`/CoreDNS service on port 53.
- The pod's `dnsPolicy`/`dnsConfig` is misconfigured, pointing it at the wrong resolver.
- A genuinely missing or misspelled Service name/namespace in the calling application's configuration (not a DNS infrastructure problem, a config problem that looks like one).

## Diagnosis Steps

1. From the affected pod, run `nslookup <service>.<namespace>.svc.cluster.local` directly — this isolates whether it's a short-name resolution issue or DNS is failing entirely.
2. `kubectl get pods -n kube-system -l k8s-app=kube-dns` — check CoreDNS pod health, restart counts, and resource usage.
3. Check CoreDNS's own logs for `SERVFAIL` patterns or upstream timeout errors.
4. Review any `NetworkPolicy` resources in the affected namespace for rules that might block egress to CoreDNS's ClusterIP/port.
5. Confirm the target Service actually exists and is spelled correctly, including namespace, in the calling application's config.

## Resolution

- CoreDNS overloaded: scale up CoreDNS replicas and/or raise its resource limits; consider enabling the `autopath`/caching plugins if query volume is the root cause.
- NetworkPolicy blocking DNS: add an explicit egress allow rule for DNS (UDP/TCP port 53) to CoreDNS's pod selector.
- Misconfigured `dnsPolicy`: correct it to `ClusterFirst` (the standard default) unless there's a specific reason to override it.
- Simple misconfiguration: fix the service name/namespace in the calling application — no infrastructure change needed.
