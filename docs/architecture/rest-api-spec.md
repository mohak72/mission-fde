# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: Incident Copilot API
  version: 0.1.0
  description: >
    Webhook ingestion API for Incident Copilot (M1). The Approval CLI and
    Eval Harness are separate local entry points into the same codebase,
    not REST clients, and are intentionally not specified here.
servers:
  - url: http://localhost:8000
    description: Local development
  - url: https://incident-copilot.internal
    description: OKE-deployed instance (Story 4.3)

paths:
  /health:
    get:
      summary: Liveness/readiness probe
      description: Used by the Kubernetes deployment (Story 4.3) for health checks.
      operationId: getHealth
      responses:
        "200":
          description: Service is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok

  /webhook/alert:
    post:
      summary: Ingest a simulated Prometheus alert
      description: >
        FR1/FR2/NFR9. Requires a valid HMAC signature header. Duplicate
        alert_ids within the dedup window are accepted but do not trigger
        a second pipeline run.
      operationId: ingestAlert
      security:
        - hmacSignature: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/AlertPayload"
      responses:
        "202":
          description: Alert accepted (new or deduplicated)
          content:
            application/json:
              schema:
                type: object
                properties:
                  alert_id:
                    type: string
                  status:
                    type: string
                    enum: [accepted, deduplicated]
        "400":
          description: Malformed payload
        "401":
          description: Missing or invalid signature (NFR9)

components:
  securitySchemes:
    hmacSignature:
      type: apiKey
      in: header
      name: X-Signature
      description: HMAC-SHA256 signature over the raw request body, per NFR9.

  schemas:
    AlertPayload:
      type: object
      required: [alert_id, labels, annotations, startsAt]
      properties:
        alert_id:
          type: string
          description: Unique identifier for dedup (FR2).
        labels:
          type: object
          additionalProperties:
            type: string
          description: Prometheus-style labels (alertname, severity, team, etc.)
        annotations:
          type: object
          additionalProperties:
            type: string
        startsAt:
          type: string
          format: date-time
```

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- I added `GET /health` even though no PRD story explicitly requests it — it's required by Story 4.3's Kubernetes deployment (liveness/readiness probes are how K8s knows to restart a crashed pod, which is literally what Story 4.3 AC4's "break → auto-heal" demo depends on). Calling this out as scope I added, not scope you asked for, consistent with how I flagged PRD additions earlier.
- I deliberately did *not* add a REST endpoint for the Approval CLI or for inspecting pipeline runs — per the PRD, approval is CLI-based and nothing requires a query API. If you want a demo-friendly "GET /runs/{id}" for Epic 6's video, say so now; it's cheap to add but wasn't asked for.
- The `AlertPayload` schema's `labels`/`annotations` shape mirrors real Alertmanager webhook JSON, so the simulated payloads double as a faithful rehearsal for the real integration this program explicitly defers (RFC non-goals).

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Database Schema)
2. Add a GET /runs/{id} endpoint for demo/debugging purposes
3. Challenge from a different stakeholder's perspective (e.g., a future Alertmanager integrator reading this spec)
4. Analyze what could go wrong if the HMAC secret itself needs rotation — does this spec/design support that?
5. Identify hidden assumptions in treating `/health` as unauthenticated (should it be?)
6. Red Team: argue the Approval CLI should actually be a REST API too, for future Slack/Telegram integration reuse
7. Tree of Thoughts: 3 alternative webhook authentication schemes, compared (HMAC vs. shared secret vs. mTLS)
8. Self-Consistency check: re-derive this API spec independently from FR1/FR2/NFR9 and diff
9. Meta-review: critique this spec as if you were Dev about to implement Story 1.2
