# HorizontalPodAutoscaler Not Scaling

## Symptoms

- Application is under heavy load (high latency, queueing requests) but `kubectl get hpa` shows the replica count unchanged.
- `kubectl describe hpa <name>` shows `unable to fetch metrics` or `missing request for cpu` warnings.
- `TARGETS` column in `kubectl get hpa` shows `<unknown>/80%` instead of an actual percentage.
- No scaling events appear in `kubectl describe hpa`'s Events section despite sustained load.

## Likely Causes

- The target Deployment's containers don't specify `resources.requests` for the metric the HPA is scaling on (commonly CPU) — the HPA has nothing to compute a percentage against.
- The metrics pipeline itself is broken: the metrics-server isn't running, is unreachable, or is reporting stale data.
- The HPA's `minReplicas`/`maxReplicas` bounds are set such that it's already at `maxReplicas` and simply can't scale further (this looks like "not scaling" but is actually scaling correctly, just capped).
- A custom/external metrics adapter (for non-CPU/memory scaling) is misconfigured or its backing metric isn't being populated.

## Diagnosis Steps

1. `kubectl describe hpa <name>` — check both the Conditions and Events sections for the specific failure reason.
2. `kubectl get deployment <name> -o yaml` — confirm `resources.requests` is actually set on every container the HPA cares about.
3. `kubectl get pods -n kube-system -l k8s-app=metrics-server` — confirm the metrics server itself is healthy.
4. `kubectl top pods` — if this also fails/returns nothing, the metrics pipeline is broken cluster-wide, not just for this HPA.
5. Check current replica count against `maxReplicas` to rule out a capacity ceiling being mistaken for a scaling failure.

## Resolution

- Missing resource requests: add `resources.requests.cpu` (and/or memory) to the target Deployment's container spec — the HPA cannot compute a percentage without this baseline.
- Broken metrics-server: fix/restart the metrics-server deployment; this is a cluster-level dependency, not something fixable per-HPA.
- At `maxReplicas` ceiling: this isn't a bug — raise `maxReplicas` if the workload genuinely needs more headroom, after confirming the node pool can actually support it.
- Custom metrics adapter issue: verify the adapter's own health and that the underlying metric source is actually emitting data.
