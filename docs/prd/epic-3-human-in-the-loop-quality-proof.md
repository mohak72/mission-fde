# Epic 3 Human-in-the-Loop & Quality Proof

Epic Goal: Make the product trustworthy and measurable — the gateway gets caching/rate-limiting discipline, the approval gate becomes real (not a stub), and a repeatable eval produces the numbers the whole product is judged on.

## Story 3.1 LLM Response Caching (LRU)

As a platform operator,
I want LLM/embedding responses cached,
so that repeated identical calls don't re-incur cost/latency and we have a benchmarked hit-rate number to quote.

### Acceptance Criteria

1: The LLM gateway caches responses for identical (model, prompt) pairs using an LRU eviction policy with a configurable max size.
2: Cache hit-rate is measured and reported via a benchmark against a fixture set of repeated/near-repeated queries.
3: Cache is transparent to callers — no call site needs to know whether a response was cached or live.
4: Unit tests cover cache hit, cache miss, eviction under capacity pressure.

## Story 3.2 Rate Limiting & Alert Dedup

As a platform operator,
I want the gateway to enforce a token-bucket rate limit and alert ingestion to merge near-duplicate alerts by interval,
so that a noisy alert storm doesn't blow the model budget or spam the approval queue.

### Acceptance Criteria

1: The LLM gateway enforces a token-bucket rate limiter (parameters configurable, not hardcoded — see Key Risks); requests over the limit are queued or rejected with a clear error, never silently dropped.
2: Alerts for the same underlying issue arriving within a configurable time window are merged (interval-merge) into a single pipeline run instead of N separate diagnoses.
3: Unit tests cover: limiter allows under limit, blocks over limit, recovers after window; interval-merge merges overlapping alerts and leaves non-overlapping ones separate.

## Story 3.3 Human Approval Gate (CLI)

As an on-call engineer,
I want to see the proposed diagnosis and action and explicitly approve or reject it,
so that no action is ever taken without my sign-off.

### Acceptance Criteria

1: After a proposal is generated, a CLI command displays the diagnosis, evidence, and proposed action, and prompts for approve/reject.
2: An approval is logged with actor + timestamp and marks the proposal "approved — would execute" (no real executor exists yet for MVP).
3: A rejection is logged with actor + timestamp and the run ends as a no-op — nothing is executed.
4: The human-approval stub from Story 2.2 is replaced by this real implementation.
5: This fulfills FR6/FR7 — the literal "demo moment" from the RFC.

## Story 3.4 Evaluation Harness

As a product owner,
I want a repeatable eval scoring retrieval hit-rate and diagnosis usefulness on a fixed 20-incident set,
so that I have a quotable, defendable quality number instead of a vibe.

### Acceptance Criteria

1: A fixed synthetic set of 20 incidents exists, each with a known-correct expected runbook.
2: Running the eval reports retrieval hit-rate (% correct runbook retrieved) across the full set.
3: Running the eval reports an LLM-judge usefulness score per diagnosis, via a judge call distinct from the diagnosis call itself.
4: The eval runs as a single command and produces a persisted report (JSON/markdown) that can be committed or attached to a PR.
5: Target retrieval hit-rate ≥80% (FR8) — if below, this is flagged as a known gap, not hidden.
