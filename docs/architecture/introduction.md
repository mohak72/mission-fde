# Introduction

This document outlines the overall project architecture for Incident Copilot (M1), including backend systems, shared platform services, and non-UI concerns. Its primary goal is to serve as the guiding architectural blueprint for AI-driven development, ensuring consistency and adherence to chosen patterns and technologies — and, per the PRD's framing, to lay down the platform (gateway, eval harness, deploy pipeline) that M2–M6 reuse.

**Relationship to Frontend Architecture:** Not applicable. Per the PRD, MVP interaction is CLI-only; there is no significant UI, so no separate Frontend Architecture Document is produced.

## Starter Template or Existing Project

Greenfield project. No starter template or existing codebase is referenced in the PRD or RFC. Proceeding with architecture design from scratch — manual setup required for all tooling and configuration (FastAPI project layout, CI workflow, Dockerfile, Terraform modules). **N/A beyond this note.**

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-11-04 | 0.1 | Initial architecture draft for M1 Incident Copilot, derived from PRD + RFC | Winston (Architect) |
