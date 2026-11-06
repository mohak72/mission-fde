# Service Has No Endpoints (Selector Mismatch)

## Symptoms

- Clients calling a Service (by name or ClusterIP) get connection refused or timeouts, even though the backing pods appear `Running` and healthy individually.
- `kubectl get endpoints <service-name>` shows an empty or `<none>` endpoints list.
- `kubectl describe service <service-name>` shows the configured `Selector`, which — on inspection — doesn't match any running pod's labels.
- The pods themselves pass their own liveness/readiness probes; the problem is purely at the Service-to-pod routing layer, not the pods' health.

## Likely Causes

- A label on the Deployment/pod template was changed (e.g., during a refactor or a version bump like `app: myapp-v2`) without updating the Service's `selector` to match.
- The Service's `selector` has a typo relative to the pod labels (easy to introduce when selectors are copy-pasted across environments).
- Pods exist and are healthy, but their `readinessProbe` is failing — a Service only routes to pods that are both label-matched *and* Ready, so a readiness failure can also produce empty endpoints even with a correct selector.
- The Service and pods are in different namespaces (a Service only selects pods within its own namespace, regardless of label match).

## Diagnosis Steps

1. `kubectl get endpoints <service-name>` — confirm the endpoints list is actually empty; this is the definitive symptom of this failure mode specifically.
2. `kubectl get service <service-name> -o yaml` — note the exact `spec.selector` key/value pairs.
3. `kubectl get pods --show-labels` — compare pod labels directly against the Service's selector, looking for a mismatch or typo.
4. `kubectl get pods -o wide` — confirm the pods are in the same namespace as the Service.
5. If labels match exactly, check `kubectl describe pod` for readiness probe failures — the selector may be correct but the pods aren't Ready.

## Resolution

- Label/selector mismatch: update either the Service's `selector` or the pod template's `labels` so they match exactly — treat this as a single source of truth going forward (e.g., keep selector labels minimal and stable, separate from other descriptive labels that change more often).
- Readiness probe failing: this is actually a different failure mode wearing this one's symptoms — fix the underlying readiness check, not the Service.
- Namespace mismatch: move the Service to the same namespace as the pods, or vice versa — Services cannot select across namespaces.
