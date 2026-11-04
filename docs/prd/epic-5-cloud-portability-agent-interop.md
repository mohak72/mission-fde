# Epic 5 Cloud Portability & Agent Interop

Epic Goal: Prove the abstraction boundaries from Epics 1–4 actually hold by swapping providers behind them, and open a second, agent-native way to use the product without creating a second implementation.

## Story 5.1 OCI Gen AI & DB 23ai Swap

As a platform operator,
I want to swap the LLM provider to OCI Gen AI and the vector store to Oracle DB 23ai behind the existing gateway/retrieval interfaces,
so that the NFR1/NFR8 abstraction claims are proven true, not just assumed.

### Acceptance Criteria

1: The LLM gateway's underlying provider is swapped to OCI Gen AI without any change to call sites outside the gateway module (proves NFR1).
2: The vector store is swapped from Chroma to Oracle DB 23ai vector search without any change to call sites outside the retrieval interface (proves NFR8).
3: The full eval harness (Story 3.4) is re-run against the OCI-native configuration and the hit-rate/judge numbers are reported alongside the original, for comparison.
4: Any behavioral differences (latency, cost, quality) between the two configurations are documented.

## Story 5.2 FastMCP Tool Interface

As an external agent (e.g., Claude Code),
I want to call "triage this alert" as an MCP tool,
so that Incident Copilot's diagnosis capability can be used programmatically outside its own webhook/CLI surface.

### Acceptance Criteria

1: A FastMCP server exposes a `triage_alert` tool taking an alert payload and returning the diagnosis — reusing the same pipeline as the webhook path, not a separate implementation.
2: The tool is demonstrably callable from Claude Code (or an equivalent MCP client) end-to-end.
3: The MCP transport is subject to the same gateway rate-limiting/caching as the webhook transport — no bypass of NFR1 via a second entry point.
4: Tests cover a successful tool call and an invalid-payload tool call.
