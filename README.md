# EngFleet

## Idea

The idea with this project is to build a fleet of Agents whose purpose is to make engineering operations simpler and automated.

## Dev

Run the ADK web UI:

```bash
cd agents
adk web
```

Run the cyber intel agent programmatically:

```bash
cd agents
 uv run -m cyber_intel.cyber_intel_client
```

Run the cyber intel agent as an a2a server:

```bash
cd agents
uv run -m cyber_intel.a2a_server
```

Request the agent card from the locally running server:

```bash
curl http://localhost:10003/.well-known/agent.json | jq
```

## 🔗 Links

- https://codelabs.developers.google.com/instavibe-adk-multi-agents/instructions#0
