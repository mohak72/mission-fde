# Node NotReady

## Symptoms

- `kubectl get nodes` shows a node's `STATUS` as `NotReady`.
- Pods scheduled on that node show as `Unknown` or begin being evicted/rescheduled elsewhere after the toleration period.
- `kubectl describe node <node>` shows stale `Ready` condition timestamps — the kubelet hasn't reported in.
- Cluster-wide alerting may fire for reduced capacity if enough nodes are affected.

## Likely Causes

- The kubelet process on the node has crashed or hung (resource exhaustion on the node itself, not just a pod).
- Network partition between the node and the control plane — the node is actually fine, but can't report status.
- The node ran out of disk space, memory, or PIDs at the OS level, causing the kubelet to become unresponsive (distinct from a pod-level OOM — this is the node itself under pressure).
- An underlying infrastructure failure (VM host issue, cloud provider instance problem).

## Diagnosis Steps

1. `kubectl describe node <node>` — read the `Conditions` section for which specific condition is failing (`Ready`, `MemoryPressure`, `DiskPressure`, `PIDPressure`, `NetworkUnavailable`).
2. If cluster access to the node exists (SSH or cloud console), check kubelet's own logs/status (`systemctl status kubelet`, `journalctl -u kubelet`).
3. Check node-level resource usage (disk, memory, inode count) directly on the host, not just via Kubernetes metrics, since a dead kubelet won't report metrics.
4. Check cloud provider status/console for the underlying VM/instance health.

## Resolution

- Kubelet crashed/hung: restart the kubelet service; if it keeps crashing, check its logs for the root cause (often a disk-full condition preventing it from writing state).
- Node resource exhaustion: free up disk/memory/PIDs, or resize the node; this is often caused by unbounded log growth or orphaned container images accumulating on the node.
- Network partition: this is an infrastructure/networking fix, not a Kubernetes config fix — escalate to whoever owns network/cloud infrastructure.
- Underlying infra failure: cordon and drain the node (`kubectl cordon`/`kubectl drain`), let the cloud provider replace the underlying instance, and let the cluster autoscaler (if present) provision a replacement.
