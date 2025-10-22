# Orchestrate Agent

A resilient, configurable agent orchestrator that manages task delegation across multiple specialized agents using Google's ADK and A2A protocols.

## Features

### Core Orchestration
- **Multi-Agent Task Delegation**: Intelligently routes tasks to appropriate specialized agents
- **Sequential Workflow Support**: Handles complex multi-step operations with dependencies
- **Domain-Aware Instructions**: Configurable instruction templates for different domains (security, general, etc.)

### Resilience & Reliability
- **Circuit Breaker Pattern**: Prevents cascading failures by temporarily disabling unresponsive agents
- **Retry Logic**: Exponential backoff retry for transient failures
- **Health Monitoring**: Continuous health checks for all connected agents
- **Graceful Degradation**: Continues operation even when some agents are unavailable

### Observability & Monitoring
- **Metrics Collection**: Tracks message counts, error rates, and response times
- **Structured Logging**: Configurable logging levels with diagnostic mode
- **Health Status API**: Real-time health status of all agents
- **Performance Monitoring**: Response time tracking and statistics

### Configuration
- **Environment-Based Config**: Configurable via environment variables
- **Domain Selection**: Choose between security-focused or general orchestration
- **Diagnostic Mode**: Enable detailed logging for troubleshooting

## Configuration

### Environment Variables

```bash
# Agent Addresses (comma-separated)
REMOTE_AGENT_ADDRESSES=http://localhost:10003,http://localhost:10004

# Domain Configuration
ORCHESTRATOR_DOMAIN=security  # or 'general'

# Logging Configuration
ORCHESTRATOR_LOG_LEVEL=INFO   # DEBUG, INFO, WARNING, ERROR
ORCHESTRATOR_DIAGNOSTIC_MODE=false  # true for verbose logging

# Circuit Breaker Settings (optional)
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
```

### Domain Modes

#### Security Mode (`ORCHESTRATOR_DOMAIN=security`)
- Specialized for cybersecurity workflows
- Pre-configured for Intigriti and Cyber Intelligence agents
- Security-specific terminology and workflows

#### General Mode (`ORCHESTRATOR_DOMAIN=general`)
- Generic orchestration for any domain
- Adaptable instruction templates
- Broad agent compatibility

## Architecture

### Core Components

1. **HostAgent**: Main orchestration logic and state management
2. **CircuitBreaker**: Failure prevention and recovery
3. **OrchestrationMetrics**: Performance monitoring and statistics
4. **RemoteAgentConnections**: A2A protocol communication layer

### Key Methods

- `send_message()`: Main task delegation with resilience features
- `_check_agent_health()`: Individual agent health verification
- `_perform_health_checks()`: Bulk health status checking
- `get_metrics()`: Access to performance statistics
- `get_health_status()`: Real-time agent health status

## Usage Examples

### Basic Task Delegation
```python
# Agent automatically routes to appropriate specialized agent
"Analyze this security threat and check for related vulnerabilities"
```

### Multi-Step Workflows
```python
# Orchestrator handles sequencing automatically
"Check Intigriti programs and then analyze any threats found"
```

### Health Monitoring
```python
# Check agent status
health = await orchestrator.get_health_status()
print(f"Agent health: {health}")

# Get performance metrics
metrics = orchestrator.get_metrics()
print(f"Performance stats: {metrics}")
```

## Resilience Features

### Circuit Breaker
- **Failure Threshold**: 3 consecutive failures trigger circuit opening
- **Recovery Timeout**: 60 seconds before attempting recovery
- **Half-Open State**: Allows single test requests during recovery

### Retry Logic
- **Max Retries**: 3 attempts per message
- **Exponential Backoff**: 2^attempt seconds delay
- **Configurable**: Retry parameters can be adjusted

### Health Monitoring
- **Check Interval**: Configurable health check frequency
- **Timeout**: 5-second timeout for health checks
- **Automatic Recovery**: Failed agents are rechecked periodically

## Monitoring & Metrics

### Available Metrics
- **Message Counts**: Per-agent message statistics
- **Error Rates**: Failure tracking by agent
- **Response Times**: Performance monitoring
- **Health Status**: Real-time agent availability

### Logging Levels
- **Normal Operation**: INFO and above
- **Diagnostic Mode**: DEBUG level with connection details
- **Errors**: Always logged regardless of level

## Development

### Testing
```bash
# Import and test agent
from agent import root_agent, host_agent_singleton

# Check features are available
assert hasattr(host_agent_singleton, '_circuit_breaker')
assert hasattr(host_agent_singleton, '_metrics')
```

### Extending
```python
# Add custom domain
def _custom_instruction(self, current_agent: dict) -> str:
    # Custom instruction logic
    pass

# Add to root_instruction method
if domain == "custom":
    return self._custom_instruction(current_agent)
```

## Compatibility

- **ADK Version**: Compatible with google-adk patterns
- **A2A Protocol**: Full compliance with Agent-to-Agent messaging
- **Python**: 3.13+ with modern type annotations
- **Dependencies**: httpx, pydantic, standard library extensions

## Troubleshooting

### Common Issues

1. **Agent Connection Failures**
   - Check `REMOTE_AGENT_ADDRESSES` configuration
   - Verify agent services are running
   - Enable diagnostic mode for connection details

2. **Circuit Breaker Triggered**
   - Check agent health status
   - Review recent error logs
   - Circuit breaker auto-recovers after timeout

3. **High Latency**
   - Check response time metrics
   - Verify network connectivity
   - Monitor agent performance

### Diagnostic Mode
Enable detailed logging:
```bash
export ORCHESTRATOR_DIAGNOSTIC_MODE=true
export ORCHESTRATOR_LOG_LEVEL=DEBUG
```

This provides comprehensive connection and operation logging for troubleshooting.
