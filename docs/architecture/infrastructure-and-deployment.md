# Infrastructure and Deployment

## Infrastructure as Code

- **Tool:** Terraform 1.9.x
- **Location:** `infra/terraform/`
- **Approach:** Terraform provisions the OKE cluster and any supporting cloud resources (networking, IAM for Bedrock access from OCI compute). No cloud resource for this project is ever created by clicking a console — if Terraform didn't make it, it isn't real infrastructure for this project (PRD NFR2).

## Deployment Strategy

- **Strategy:** GitOps — ArgoCD continuously syncs the deployed state to what's declared in Git; there is no `kubectl apply`/`helm install` run by a human against the target cluster, ever (PRD NFR2, Story 4.3 AC3).
- **CI/CD Platform:** GitHub Actions (lint + test from Story 1.1; + eval-gate from Story 4.2)
- **Pipeline Configuration:** `.github/workflows/ci.yaml`

## Environments

- **Local:** `kind` cluster, developer machine - target for Story 2.3's kubectl tool during development and for integration tests; Postgres + Chroma run via `docker-compose.yaml`.
- **Deployed (OKE):** The one real deployed environment for M1 MVP — per PRD NFR6 (single-cluster, single-tenant scope), there is deliberately no separate staging/prod split. This is the environment Story 4.3's deploy and Story 6.1's demo both point at.

## Environment Promotion Flow

```text
developer commit → PR opened
       │
       ▼
GitHub Actions CI (lint, unit+integration tests, eval-gate from Story 4.2)
       │  (must pass)
       ▼
PR merged to main
       │
       ▼
ArgoCD detects new main state → syncs OKE deployment automatically
       │
       ▼
Deployed service running on OKE (Story 4.3 AC5: responds to real webhook call)
```

There is exactly one promotion step (merge to main → auto-deploy) because there is exactly one deployed environment. This is intentionally simpler than a typical dev→staging→prod pipeline — adding environments this project doesn't need would be scope creep, not rigor.

## Rollback Strategy

- **Primary Method:** `git revert` the offending commit on `main`; ArgoCD detects the reverted state and syncs the cluster back automatically. No manual `kubectl rollout undo` — rollback follows the same GitOps path as forward deploys (consistency, not a special case).
- **Trigger Conditions:** CI failure *after* merge is not possible by construction (CI gates the merge, per Story 1.1/4.2) — rollback is for a regression CI didn't catch (e.g., a live-traffic-only failure, or Story 4.3 AC4's deliberate-failure test revealing a real bug rather than a demo).
- **Recovery Time Objective:** Not formally specified — this is a single-demo-environment learning project, not a production SLA-bound service; I'm flagging this as an explicit, deliberate non-requirement rather than a silent gap.

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- Single-environment (no staging) is a direct consequence of PRD NFR6 — worth double-checking you're fine with zero staging buffer before a demo-breaking regression reaches the one environment the demo video (Epic 6) depends on. The eval-gate (Story 4.2) is the main safety net here.
- No formal RTO — I could invent a number, but that would be theater for a one-person learning project; I'd rather name the gap than fabricate false rigor.

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Error Handling Strategy)
2. Expand on what a minimal staging step would look like if you want one before Epic 6's demo recording
3. Challenge from a different stakeholder's perspective (e.g., an SRE interviewer asking "what's your rollback story")
4. Analyze what could go wrong with ArgoCD auto-sync deploying a broken commit straight to the only environment
5. Identify hidden assumptions in "CI failure after merge is not possible by construction"
6. Red Team: argue for a staging environment even for a one-person project, given the "YC-grade, not demo" bar
7. Tree of Thoughts: 3 alternative rollback mechanisms, compared
8. Self-Consistency check: re-derive this section independently from NFR2/NFR6 and diff
9. Meta-review: critique this section as if you were the infra-devops-platform agent about to write the actual Terraform/ArgoCD manifests
