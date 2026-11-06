# Database Connection Pool Exhaustion

## Symptoms

- Application logs show errors like `connection pool exhausted`, `timeout waiting for connection`, or `too many clients already` (from the database side).
- Request latency spikes sharply and error rates climb, but CPU/memory on the application pods look normal — the bottleneck is connection availability, not compute.
- `kubectl logs` for the application shows requests queueing on a connection checkout before even reaching the database.
- The database server itself may log its own `max_connections` limit being hit if the exhaustion is severe enough to reach the server, not just the application's local pool.

## Likely Causes

- A traffic spike exceeds the configured pool size, and the pool wasn't sized for peak load.
- A connection leak: code paths that acquire a connection but fail to release it on an error path (common when exception handling skips a `finally`/context-manager release).
- A slow query (missing index, lock contention) holds connections checked out for far longer than normal, starving the pool even at otherwise-normal request volume.
- A recent horizontal scale-up of the application (more pods, each with its own pool) collectively exceeds the database server's own `max_connections` limit, even though each individual pod's pool looks reasonably sized.

## Diagnosis Steps

1. Check application-level pool metrics if exposed (active/idle/waiting connection counts) — a steadily climbing "waiting" count with flat "idle" points at exhaustion, not just load.
2. Check the database server's current connection count against its `max_connections` setting.
3. Look for unusually long-running queries or lock waits on the database side — these hold connections open longer than expected.
4. Review recent deploys for error-handling code paths that might skip connection release, and recent scaling events that increase total pods (and thus total pool capacity demanded of the database).

## Resolution

- Pool undersized for load: increase the application's pool size, but only after confirming the database server's `max_connections` has headroom for the new total across all pods.
- Connection leak: this is a code bug — audit error-handling paths to ensure connections are always released (context managers / `finally` blocks), not a configuration fix.
- Slow queries holding connections: fix the query (add an index, reduce lock scope) rather than just adding more connections to mask the symptom.
- Fleet-wide pool size exceeding database capacity after scale-up: use a connection pooler (e.g., PgBouncer-style) between the application fleet and the database so total backend connections stay bounded regardless of pod count.
