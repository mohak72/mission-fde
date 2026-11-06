# Node Disk Pressure Causing Pod Eviction

## Symptoms

- Pods on a node are evicted with `kubectl describe pod` showing `The node was low on resource: ephemeral-storage` or similar.
- `kubectl get events` shows `Evicted` pods with reason `DiskPressure`.
- `kubectl describe node <node>` shows the `DiskPressure` condition as `True`.
- Pods may be rescheduled to other nodes, potentially triggering a cascade if those nodes are also near their disk threshold.

## Likely Causes

- Container logs written to stdout/stderr accumulate on the node's disk faster than log rotation/shipping can clear them (common with noisy or misconfigured logging).
- Orphaned or unused container images accumulate over time without garbage collection keeping pace.
- A container writes large temporary files to its writable layer or an `emptyDir` volume without any size limit, consuming node-local disk rather than a dedicated volume.
- The node's disk was simply undersized for the workload density actually scheduled onto it.

## Diagnosis Steps

1. `kubectl describe node <node>` — confirm `DiskPressure` condition and check the eviction thresholds configured on the kubelet.
2. SSH/console into the node (if accessible) and run `df -h` to see which filesystem is actually full, and `du`-style investigation to find what's consuming it (container logs, images, emptyDir volumes).
3. `kubectl get events --field-selector reason=Evicted` — identify which pods were evicted and correlate with what they write to local disk.
4. Check image garbage collection settings on the kubelet (`--image-gc-high-threshold`/`--image-gc-low-threshold`) to see if they're too permissive for this node's disk size.

## Resolution

- Log growth: fix log rotation configuration, or move to a log-shipping sidecar/DaemonSet that ships logs off-node faster than they accumulate.
- Image accumulation: tune kubelet image garbage collection thresholds, or trigger a manual prune if the node is already critical.
- Unbounded emptyDir/writable-layer usage: set `sizeLimit` on `emptyDir` volumes, or move the workload to use a dedicated PVC with its own quota instead of node-local storage.
- Undersized node: resize the node or rebalance workload density (lower max pods per node, or use larger nodes) so expected disk usage leaves real headroom.
