# Pod CrashLoopBackOff: Out of Memory (OOMKilled)

## Symptoms

- Pod status cycles through `CrashLoopBackOff`.
- `kubectl describe pod` shows `Last State: Terminated`, `Reason: OOMKilled`, `Exit Code: 137`.
- Restart count climbs steadily; the interval between restarts follows Kubernetes' exponential backoff.
- Application logs cut off abruptly mid-request, with no graceful shutdown message.

## Likely Causes

- The container's memory usage exceeded its configured `resources.limits.memory`.
- A memory leak in the application causes usage to grow unbounded over the pod's uptime.
- The memory limit was set too low relative to the workload's actual steady-state or peak usage (e.g., a batch job processing a larger-than-expected payload).

## Diagnosis Steps

1. `kubectl describe pod <pod>` — confirm `OOMKilled` in the terminated container's state.
2. `kubectl top pod <pod>` — check current memory usage against the configured limit.
3. Check the memory usage trend over the pod's lifetime (via metrics/dashboards if available) — a leak shows steadily rising usage; a limit-too-low issue shows usage pinned at the ceiling shortly after startup.
4. Review recent deployments or config changes that could have increased memory footprint (new dependency, larger batch size, a new in-memory cache).

## Resolution

- If this is a one-off spike: raise `resources.limits.memory` to a value with headroom above observed peak usage, and set `resources.requests.memory` to the typical steady-state usage.
- If this is a genuine leak: this is a code-level bug, not a configuration fix — track down the leaking allocation (unclosed connections, unbounded caches, accumulating event listeners) before resizing the limit, since a bigger limit only delays the same crash.
- Add alerting on memory usage approaching the limit (e.g., 80% threshold) so this is caught before the OOM kill, not just diagnosed after.
