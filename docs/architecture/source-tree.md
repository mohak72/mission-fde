# Source Tree

This is fully pinned (no starter template was used, per the Introduction section — this tree is what substitutes for one):

```
Mission-FDE/
├── .github/
│   └── workflows/
│       └── ci.yaml                     # Story 1.1: lint+test; Story 4.2: + eval-gate
├── apps/
│   └── incident-copilot/
│       ├── pyproject.toml
│       ├── src/incident_copilot/
│       │   ├── main.py                 # FastAPI app entrypoint
│       │   ├── api/
│       │   │   ├── webhook.py          # POST /webhook/alert (Story 1.2)
│       │   │   └── health.py           # GET /health (Story 4.3)
│       │   ├── mcp/
│       │   │   └── server.py           # FastMCP triage_alert tool (Story 5.2)
│       │   ├── ingestion/
│       │   │   ├── auth.py             # HMAC verification (NFR9)
│       │   │   ├── dedup.py            # dedup + interval-merge (FR2, Story 3.2)
│       │   │   └── pii.py              # PII scrubber (FR10)
│       │   ├── graph/
│       │   │   ├── pipeline.py         # LangGraph definition, run_pipeline() (Story 2.2)
│       │   │   └── nodes/
│       │   │       ├── classify.py
│       │   │       ├── retrieve.py
│       │   │       ├── investigate.py
│       │   │       ├── propose.py
│       │   │       └── approve.py
│       │   ├── retrieval/
│       │   │   ├── interface.py        # RetrievalService seam (NFR8)
│       │   │   ├── chroma_backend.py
│       │   │   └── oracle_backend.py   # added at Story 5.1
│       │   ├── cluster/
│       │   │   └── evidence.py         # Cluster Evidence Tool (Story 2.3) - read-only guard lives here
│       │   ├── approval/
│       │   │   └── cli.py              # Approval CLI (Story 3.3)
│       │   ├── eval/
│       │   │   ├── harness.py          # Eval Harness (Story 3.4), also invoked by CI
│       │   │   └── incidents/          # fixed 20-incident synthetic set
│       │   ├── persistence/
│       │   │   ├── models.py           # SQLAlchemy models matching Database Schema
│       │   │   ├── repositories.py     # one repository class per model
│       │   │   └── migrations/         # Alembic
│       │   └── config.py               # pydantic-settings (NFR7 - only module reading raw env vars)
│       ├── runbooks/                    # 10+ markdown runbooks (Story 1.3)
│       └── tests/
│           ├── unit/
│           ├── integration/             # runs against local kind cluster + Postgres
│           └── conftest.py
├── platform/                            # reused wholesale by M2-M6
│   ├── pyproject.toml
│   └── src/platform_core/
│       ├── gateway/
│       │   ├── gateway.py               # LLM Gateway complete() (NFR1 - only seam to any model provider)
│       │   ├── rate_limiter.py          # token-bucket (Story 3.2)
│       │   ├── cache.py                 # LRU cache (Story 3.1)
│       │   ├── bedrock_provider.py
│       │   └── oci_provider.py          # added at Story 5.1
│       └── tracing/
│           └── langfuse_wrapper.py      # Story 4.1
├── infra/
│   ├── terraform/                       # OKE provisioning (Story 4.3)
│   │   ├── main.tf
│   │   ├── oke.tf
│   │   └── variables.tf
│   └── argocd/
│       └── application.yaml             # GitOps deploy manifest (Story 4.3)
├── docs/
│   ├── design.md                        # RFC (S0, done)
│   ├── prd.md
│   ├── architecture.md
│   ├── architecture/                    # sharded by PO: coding-standards.md, tech-stack.md, source-tree.md
│   ├── stories/                         # SM-authored stories, one file per story
│   └── qa/                              # QA gate files
├── Dockerfile                            # Story 4.3
├── docker-compose.yaml                   # local dev: Postgres + Chroma + kind, for Story 1.1 onward
├── Mohak_FDE_Master_Roadmap.xlsx
└── Incident_Copilot_Build_Tracker.xlsx
```

---

**⚠️ Elicitation required before continuing.**

Rationale / flags:
- `cluster/evidence.py` is called out as where the NFR5 "static guard" (no write methods referenced, from the Components section) should live and be tested — this is the one file in the tree I'd want a dedicated test file for from day one.
- `docs/architecture/` (plural, sharded) vs. this single `docs/architecture.md` — both will exist: this file is the full source of truth; PO's upcoming `*shard-doc` run splits out `coding-standards.md`/`tech-stack.md`/`source-tree.md` into `docs/architecture/` because `core-config.yaml`'s `devLoadAlwaysFiles` points there, not at this file directly.
- `platform/` and `apps/incident-copilot/` are separate `pyproject.toml`s (not one package) — deliberate, since `platform/` is what M2–M6 will add as a dependency; keeping it independently installable now avoids a bigger refactor later.

Select 1-9 or just type your question/feedback:

1. Proceed to next section (Infrastructure and Deployment)
2. Expand on why platform/ and apps/incident-copilot/ are separate packages instead of one with internal module boundaries
3. Challenge from a different stakeholder's perspective (e.g., Dev opening this tree cold at Story 1.1 with no other context)
4. Analyze what could go wrong if `eval/incidents/` (fixture data) accidentally gets treated as production data
5. Identify hidden assumptions in using Alembic specifically for migrations
6. Red Team: argue for a flatter structure (no apps/platform split) given this is still a one-person, one-product repo today
7. Tree of Thoughts: 3 alternative directory layouts, compared
8. Self-Consistency check: re-derive this tree independently from the Components section and diff
9. Meta-review: critique this tree as if you were Dev about to run Story 1.1's scaffolding task
