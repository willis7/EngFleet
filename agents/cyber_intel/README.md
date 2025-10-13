# Cyber Intelligence Agent

## Development

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
