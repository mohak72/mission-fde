# Security

## Input Validation

- **Validation Library:** `pydantic` (already the Tech Stack choice for config and data models — one validation approach, not two).
- **Validation Location:** At the API boundary (webhook) and the MCP tool boundary, before the payload reaches the Ingestion Module's business logic — a malformed payload never reaches dedup/PII-scrub code.
- **Required Rules:** All external input validated; whitelist (explicit allowed fields/shapes) over blacklist, per the `AlertPayload` schema already defined in REST API Spec.

## Authentication & Authorization

- **Auth Method:** HMAC-SHA256 shared-secret signature on the webhook (NFR9, already specified). **Resolving the MCP-path question flagged in High Level Architecture:** the FastMCP tool requires a bearer-token shared secret (configured for the MCP client, e.g. Claude Code) — different mechanism than HMAC because MCP's transport doesn't naturally carry a signature-over-raw-body the way an HTTP webhook does, but the same requirement in spirit: no unauthenticated caller reaches the Diagnosis Graph through either entry point. This also satisfies Story 5.2 AC3 (MCP subject to the same gateway controls, not a bypass).
- **Session Management:** N/A — no user sessions anywhere; the Approval CLI records a local `actor` string per decision, not a session token.

## Secrets Management

- **Development:** `.env` file, already excluded via `.gitignore`, loaded through `config.py`'s `pydantic-settings` object (Coding Standards' single-source-of-config rule).
- **Production:** Kubernetes Secrets on OKE, populated from a vault-backed source (not plaintext in Terraform state) — Terraform should reference an external secret (e.g. OCI Vault) rather than declaring the secret value inline in a `.tf` file, which would otherwise land in Terraform state in plaintext. This is a specific, consequential decision I'm adding now rather than leaving implicit.
- **Code Requirements:** Never hardcode; access via `config.py` only; never in logs or error messages (already in Coding Standards/Error Handling).

## API Security

- **Rate Limiting:** Two layers, not one — (1) the LLM Gateway's outbound token-bucket limiter protects the model-call budget (NFR1/Story 3.2, already specified), and (2) a new addition: **inbound** rate limiting at the webhook route itself (lightweight middleware, e.g. `slowapi`), so a flood of forged/retried requests can't exhaust ingestion resources before even reaching the dedup check. Flagging this as hardening I'm adding, not something the PRD explicitly asked for.
- **CORS Policy:** Fully locked down (deny all cross-origin) — this API is server-to-server only (Alertmanager-style caller, MCP client); no browser ever calls it, so there's no legitimate CORS use case to leave open.
- **Security Headers:** Minimal — `X-Content-Type-Options: nosniff` and equivalent cheap headers via middleware; explicitly not over-investing here since this isn't a browser-facing surface.
- **HTTPS Enforcement:** TLS terminated at the OKE ingress/load balancer, not handled in application code — the app assumes it always sits behind TLS termination.

## Data Protection

- **Encryption at Rest:** Relies on OCI block storage's default volume encryption for Postgres and Chroma's local persistence — no custom app-level encryption layer, which would be disproportionate at this scale and threat model.
- **Encryption in Transit:** TLS everywhere it matters by default: ingress (webhook/MCP), Postgres connection (`sslmode=require`), Bedrock/OCI Gen AI SDK calls, Kubernetes API client (standard kubeconfig TLS).
- **PII Handling:** Scrubbed by the Ingestion Module's rule-based scrubber *before* persistence or any LLM call (FR10) — this is the same scrubber flagged as a scope decision back in Components; reaffirming its placement here as a security control, not just a data-hygiene nicety.
- **Logging Restrictions:** No raw alert payload, kubeconfig, or API key in any log or trace line — already a Coding Standards Critical Rule; restated here because Security is where a reviewer would look for it first.

## Dependency Security

- **Scanning Tool:** `pip-audit`, run as a CI step (new addition to the Story 1.1 CI pipeline).
- **Update Policy:** Dependabot opens update PRs; none auto-merge — a human (you) reviews each one, which at this project's size is more appropriate than a fully automated merge policy.
- **Approval Process:** Any new dependency added to a `pyproject.toml` needs a one-line rationale in the PR description — lightweight, not a formal ADR process, right-sized for a solo project.

## Security Testing

- **SAST Tool:** `bandit`, run as a CI step alongside `ruff` — catches common Python security antipatterns (e.g., `eval`, weak hashing) that `ruff`'s default rule set doesn't specifically target.
- **DAST Tool:** N/A — dynamic scanning against a running instance isn't justified at this project's scale/threat model; naming this explicitly as a deliberate non-requirement.
- **Penetration Testing:** N/A — out of scope and cost for this project; same reasoning.

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- The MCP bearer-token decision resolves the flag I raised two sections ago — worth you explicitly confirming this is an acceptable mechanism rather than me quietly picking one.
- Inbound rate limiting (webhook) and the vault-backed Terraform secrets pattern are both new hardening I'm adding beyond what the PRD/RFC explicitly asked for — consistent with your "real-world, not demo" bar, but they are scope additions, flagging as such.
- `bandit` + `pip-audit` are two new CI dependencies not mentioned in Tech Stack — should be added there too if you approve them here.

Select 1-9 or just type your question/feedback:

1. Proceed — output the full architecture document and run the architect-checklist
2. Expand on the vault-backed secrets pattern — what this actually looks like with Terraform + OCI Vault concretely
3. Challenge from a different stakeholder's perspective (e.g., a security reviewer doing a 30-minute audit of this whole Security section)
4. Analyze what could go wrong if the MCP bearer token is reused/leaked — blast radius compared to the webhook's HMAC scheme
5. Identify hidden assumptions in "TLS terminated at ingress, app doesn't handle it"
6. Red Team: argue DAST/pentest should NOT be dismissed as N/A, even at this scale, given this product literally calls kubectl against a cluster
7. Tree of Thoughts: 3 alternative MCP authentication schemes, compared
8. Self-Consistency check: re-derive this Security section independently from NFR7/NFR9 and diff
9. Meta-review: critique this section as if you were a security-focused interviewer grilling you on this exact document
