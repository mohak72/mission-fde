# Next Steps

## UX Expert Prompt

Not applicable for this PRD — M1 Incident Copilot's MVP interaction surface is CLI-only (human approval gate, Story 3.3); Slack/Telegram UX is explicitly deferred past MVP. Revisit this prompt when that work is scheduled.

## Architect Prompt

Use this PRD (`docs/prd.md`) plus the RFC (`docs/design.md`) as input to create the architecture document. Key things this PRD needs from you, specifically:

1. Concrete module boundaries for the "single LLM gateway" (NFR1) and "single retrieval interface" (NFR8) — these are promises this PRD makes that Epic 5 will test by swapping providers behind them; design them to actually hold.
2. A secrets-handling mechanism satisfying NFR7 (cluster kubeconfig + model API keys never logged/traced) — this PRD deliberately left the "how" to you.
3. `coding-standards.md`, `tech-stack.md`, and `source-tree.md` under `docs/architecture/` — these are referenced by `core-config.yaml`'s `devLoadAlwaysFiles` and are required before the SM can draft stories against them.
4. A concrete webhook signature/auth mechanism satisfying NFR9 (added during PM checklist review).
5. Explicit guidance on the Modular Monolith → extracted-gateway-service seam, since M2 (PipelineMedic) is already scheduled to reuse the gateway as a dependency, not duplicate it.
