# ImagePullBackOff / ErrImagePull

## Symptoms

- Pod status shows `ImagePullBackOff` or `ErrImagePull`, never reaching `Running`.
- `kubectl describe pod` shows events like `Failed to pull image`, `manifest unknown`, `unauthorized`, or `connection timed out` against the registry.
- No application logs exist at all — the container never started, so there's nothing to log.

## Likely Causes

- The image tag doesn't exist in the registry (typo, or a CI build that never pushed the expected tag).
- The registry requires authentication and the cluster's `imagePullSecrets` are missing, expired, or not referenced by the pod spec/service account.
- The image is in a private registry and the node can't reach it due to a network policy or firewall rule.
- Registry rate limiting (common with public Docker Hub images pulled frequently without authentication).

## Diagnosis Steps

1. `kubectl describe pod <pod>` — read the exact failure reason in the Events section; the three causes above produce distinguishably different messages.
2. Verify the image reference (registry/repo:tag) is correct and that tag actually exists (`docker manifest inspect` or the registry's own UI/API).
3. Check `kubectl get pod <pod> -o yaml` for `imagePullSecrets` and confirm the referenced secret exists in the namespace and hasn't expired.
4. If authentication looks correct, test registry reachability from a node directly (e.g., a debug pod on the same node attempting the same pull).

## Resolution

- Typo/missing tag: fix the image reference in the deployment manifest and ensure the CI pipeline actually pushes the tag it's deploying.
- Missing/expired credentials: recreate the `imagePullSecrets` (e.g., `kubectl create secret docker-registry`) and reference it in the pod spec or the namespace's default service account.
- Network/firewall blocking the registry: this is an infrastructure fix, not an application one — coordinate with whoever owns network policy for the cluster.
- Rate limiting: switch to an authenticated pull (even for public images) or mirror the image to an internal registry to avoid shared rate limits.
