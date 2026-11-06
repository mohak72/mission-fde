# PersistentVolumeClaim Stuck Pending / Unbound

## Symptoms

- A pod referencing a PVC stays in `Pending` state indefinitely.
- `kubectl get pvc` shows the claim's `STATUS` as `Pending` rather than `Bound`.
- `kubectl describe pod` shows `0/N nodes are available` or `pod has unbound immediate PersistentVolumeClaims`.
- `kubectl describe pvc` shows events like `no persistent volumes available for this claim` or `waiting for first consumer to be created before binding`.

## Likely Causes

- No `StorageClass` exists matching what the PVC requests, or the requested `StorageClass` has no provisioner configured.
- The requested storage size exceeds what any available PersistentVolume (or the underlying cloud provider's quota) can satisfy.
- The `StorageClass` uses `WaitForFirstConsumer` binding mode, and the PVC is legitimately waiting for a pod to be scheduled first — not actually stuck, just early in a normal sequence.
- A zone/region mismatch: the PV (or the storage backend) is pinned to an availability zone the pod's node isn't in.

## Diagnosis Steps

1. `kubectl get pvc <name> -o yaml` — check the requested `storageClassName` and `resources.requests.storage`.
2. `kubectl get storageclass` — confirm the requested class exists and has a working provisioner.
3. `kubectl describe pvc <name>` — read the Events section for the specific binding failure reason.
4. If using `WaitForFirstConsumer`, confirm whether a pod is actually scheduled yet — this binding mode is lazy by design.
5. Check the underlying cloud provider's volume/disk quota if dynamic provisioning is failing silently.

## Resolution

- Missing/misnamed StorageClass: create or correct the `StorageClass` reference in the PVC spec.
- Quota exceeded: request a quota increase from the cloud provider, or reduce the requested volume size.
- Legitimate `WaitForFirstConsumer` wait: no action needed — ensure the corresponding pod is actually being scheduled (check the pod's own scheduling events separately).
- Zone mismatch: either relax node affinity/zone constraints on the pod, or provision storage in the zone the pod is scheduled to.
