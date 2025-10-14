# EngFleet

## Idea

This project builds and manages a small fleet of autonomous agents (the “EngFleet”) for prototyping, testing, and automating engineering workflows. It leverages the ADK multi‑agent environment to run multiple cooperating agents locally, so you can iterate on agent design, orchestration, and observability before deploying to larger infrastructure.

Goals

- Provide a reproducible local development environment for multi‑agent experiments.
- Make it easy to compose, run, and iterate on agent behaviours and communication patterns.
- Surface observability (logs, traces, state) and safety controls for each agent.
- Offer reusable agent templates and configuration that map to team use cases (code review, CI triage, changelog generation, etc.).

What this repo contains (high level)

- Agent definitions and behaviour modules that implement task logic.
- Orchestration config for composing agent fleets and defining roles/permissions.
- Test harnesses and sample scenarios for validating interactions and edge cases.
- Utilities for syncing dependencies, managing a virtualenv, and launching the ADK web UI for inspection.

Intended users

- Engineers experimenting with AI agent workflows.
- Teams validating multi‑agent coordination patterns.
- Developers building automated assistants that integrate with repos, CI, and observability tooling.

How to approach development

- Use the included dev workflow to sync dependencies and open the ADK web UI to inspect agents and message flows.
- Start from the provided templates, implement a minimal agent, then expand roles and communication channels.
- Iterate with small, well‑scoped scenarios and add monitoring/assertions to surface unexpected behaviours.
- Keep agent intents explicit, limit capabilities, and add guards for actions that touch external systems.

## Dev

```bash
uv sync
source .venv/bin/activate
```

Run the ADK web UI:

```bash
cd agents
adk web
```

## 🔗 Links

- https://codelabs.developers.google.com/instavibe-adk-multi-agents/instructions#0
