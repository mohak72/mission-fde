# Pod CrashLoopBackOff: Failing Liveness Probe

## Symptoms

- Pod status cycles through `CrashLoopBackOff`.
- `kubectl describe pod` shows `Liveness probe failed` events, followed by `Killing container with id ...`.
- The container's own logs often show the process running normally right up until the kill — the application itself isn't crashing, Kubernetes is killing it.
- Restart count increases, but exit codes may vary (commonly 137 for SIGKILL after the probe grace period).

## Likely Causes

- The liveness probe's endpoint, port, or path is misconfigured (e.g., pointing at `/health` when the app serves `/healthz`).
- The probe's `initialDelaySeconds` is too short for a slow-starting application (e.g., one doing cache warmup or a large startup migration), so the first probe fires before the app is ready.
- The application is genuinely deadlocked or unresponsive (a real liveness failure, not a misconfiguration) — e.g., a thread pool exhausted, a lock held indefinitely.
- The probe's `timeoutSeconds` is too short for an endpoint that's slow under load, causing transient timeouts to be misread as failures.

## Diagnosis Steps

1. `kubectl describe pod <pod>` — read the probe failure events for the exact reason (connection refused, timeout, non-2xx response).
2. Compare the probe's configured `path`/`port` against what the application actually serves.
3. Check how long the application takes to become ready after container start (startup logs, "ready" log line timestamp) against `initialDelaySeconds`.
4. `kubectl exec` into the container (if it stays up long enough) and manually curl the health endpoint to see what it actually returns.

## Resolution

- If misconfigured: fix the probe's path/port to match the actual health endpoint.
- If the app is slow to start: increase `initialDelaySeconds`, or better, use a separate `startupProbe` with a longer allowance so the liveness probe only begins after startup is confirmed complete.
- If genuinely deadlocked: this is an application bug (thread/lock management), not a probe configuration issue — the probe is correctly protecting availability by restarting a stuck process; fix the underlying deadlock.
- If flaky under load: increase `timeoutSeconds` and `failureThreshold` modestly, but don't paper over a health endpoint that's slow because the app itself is struggling under load.
