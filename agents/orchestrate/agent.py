import asyncio
import json
import os
import time
import uuid
from typing import Any

import httpx
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)


try:
    from remote_agent_connection import (
        RemoteAgentConnections,
        TaskUpdateCallback,
    )
except ImportError:
    from orchestrate.remote_agent_connection import (
        RemoteAgentConnections,
        TaskUpdateCallback,
    )
import logging

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext


# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# --- Metrics and Monitoring ---
class OrchestrationMetrics:
    """Simple metrics collection for orchestration operations."""

    def __init__(self):
        self.message_count: dict[str, int] = {}
        self.error_count: dict[str, int] = {}
        self.response_times: list[float] = []
        self.last_health_check: dict[str, float] = {}

    def record_message(self, agent_name: str):
        """Record a message sent to an agent."""
        self.message_count[agent_name] = self.message_count.get(agent_name, 0) + 1

    def record_error(self, agent_name: str):
        """Record an error for an agent."""
        self.error_count[agent_name] = self.error_count.get(agent_name, 0) + 1

    def record_response_time(self, response_time: float):
        """Record response time."""
        self.response_times.append(response_time)
        # Keep only last 100 measurements
        if len(self.response_times) > 100:
            self.response_times.pop(0)

    def record_health_check(self, agent_name: str, healthy: bool):
        """Record health check result."""
        self.last_health_check[agent_name] = time.time()

    def get_stats(self) -> dict[str, Any]:
        """Get current metrics statistics."""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            "total_messages": sum(self.message_count.values()),
            "messages_by_agent": self.message_count.copy(),
            "errors_by_agent": self.error_count.copy(),
            "average_response_time": avg_response_time,
            "total_measurements": len(self.response_times)
        }


# --- Configuration ---
REMOTE_AGENT_ADDRESSES_STR = os.getenv("REMOTE_AGENT_ADDRESSES", "")
REMOTE_AGENT_ADDRESSES = [
    addr.strip() for addr in REMOTE_AGENT_ADDRESSES_STR.split(",") if addr.strip()
]

# Logging configuration
LOG_LEVEL = os.getenv("ORCHESTRATOR_LOG_LEVEL", "INFO").upper()
DIAGNOSTIC_MODE = os.getenv("ORCHESTRATOR_DIAGNOSTIC_MODE", "false").lower() == "true"

if DIAGNOSTIC_MODE:
    log.info(f"Remote Agent Addresses: {REMOTE_AGENT_ADDRESSES}")
    log.setLevel(getattr(logging, LOG_LEVEL))
else:
    log.setLevel(logging.WARNING)  # Only show warnings and errors in production


# --- Circuit Breaker Implementation ---
class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count: dict[str, int] = {}
        self.last_failure_time: dict[str, float] = {}
        self.state: dict[str, str] = {}  # 'closed', 'open', 'half_open'

    def is_open(self, service_name: str) -> bool:
        """Check if the circuit breaker is open for a service."""
        state = self.state.get(service_name, 'closed')
        if state == 'closed':
            return False
        elif state == 'open':
            # Check if recovery timeout has passed
            if service_name in self.last_failure_time:
                import time
                if time.time() - self.last_failure_time[service_name] > self.recovery_timeout:
                    self.state[service_name] = 'half_open'
                    return False
            return True
        elif state == 'half_open':
            return False
        return False

    def record_success(self, service_name: str):
        """Record a successful operation."""
        if service_name in self.failure_count:
            self.failure_count[service_name] = 0
        self.state[service_name] = 'closed'

    def record_failure(self, service_name: str):
        """Record a failed operation."""
        self.failure_count[service_name] = self.failure_count.get(service_name, 0) + 1
        self.last_failure_time[service_name] = time.time()

        if self.failure_count[service_name] >= self.failure_threshold:
            self.state[service_name] = 'open'
            if DIAGNOSTIC_MODE:
                log.warning(f"Circuit breaker opened for {service_name}")


# --- Helper Functions ---
def create_send_message_payload(
    text: str, task_id: str | None = None, context_id: str | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": text}],
            "messageId": uuid.uuid4().hex,
        },
    }
    if task_id:
        payload["message"]["taskId"] = task_id
    if context_id:
        payload["message"]["contextId"] = context_id
    return payload


# --- Main Agent Class ---
class HostAgent:
    """The orchestrate agent with a special diagnostic initializer."""

    def __init__(self, task_callback: TaskUpdateCallback | None = None):
        log.info("HostAgent instance created in memory (uninitialized).")
        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self.is_initialized = False
        self._circuit_breaker = CircuitBreaker()
        self._metrics = OrchestrationMetrics()

    async def _initialize(self):
        """Initialize connections to remote agents."""
        if not REMOTE_AGENT_ADDRESSES:
            log.error("No remote agent addresses configured. Set REMOTE_AGENT_ADDRESSES environment variable.")
            self.is_initialized = True
            return

        async with httpx.AsyncClient(timeout=30) as client:
            for address in REMOTE_AGENT_ADDRESSES:
                try:
                    if DIAGNOSTIC_MODE:
                        log.info(f"Connecting to agent at: {address}")

                    card_resolver = A2ACardResolver(client, address)
                    card = await card_resolver.get_agent_card()

                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card

                    if DIAGNOSTIC_MODE:
                        log.info(f"Successfully connected to agent: {card.name}")

                except Exception as e:
                    log.error(f"Failed to connect to agent at {address}: {e}")
                    if DIAGNOSTIC_MODE:
                        log.exception("Full exception details:")

        if not self.remote_agent_connections:
            log.error("No agents could be connected. Orchestrator will not function properly.")
        else:
            agent_info = [
                json.dumps({"name": c.name, "description": c.description})
                for c in self.cards.values()
            ]
            self.agents = "\n".join(agent_info)
            log.info(f"Initialization complete. Connected to {len(self.remote_agent_connections)} agents.")

        self.is_initialized = True

    async def _check_agent_health(self, agent_name: str) -> bool:
        """Check if a specific agent is healthy and responsive."""
        if agent_name not in self.remote_agent_connections:
            return False

        try:
            # Simple health check - try to get the agent card
            connection = self.remote_agent_connections[agent_name]
            async with httpx.AsyncClient(timeout=5) as client:
                card_resolver = A2ACardResolver(client, connection.card.url)
                card = await card_resolver.get_agent_card()
                healthy = card is not None
                self._metrics.record_health_check(agent_name, healthy)
                return healthy
        except Exception as e:
            if DIAGNOSTIC_MODE:
                log.warning(f"Health check failed for agent {agent_name}: {e}")
            self._metrics.record_health_check(agent_name, False)
            return False

    async def _perform_health_checks(self) -> dict[str, bool]:
        """Perform health checks on all connected agents."""
        health_status = {}
        for agent_name in self.remote_agent_connections:
            health_status[agent_name] = await self._check_agent_health(agent_name)
        return health_status

    async def before_agent_callback(self, callback_context: CallbackContext):
        log.info("`before_agent_callback` triggered.")
        if not self.is_initialized:
            await self._initialize()

        state = callback_context.state
        if "session_active" not in state or not state["session_active"]:
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            state["session_active"] = True

    def root_instruction(self, context: ReadonlyContext) -> str:
        """Generate the orchestrator instruction based on available agents."""
        current_agent = self.check_active_agent(context)

        # Domain-specific configuration
        domain = os.getenv("ORCHESTRATOR_DOMAIN", "general")
        if domain == "security":
            return self._security_instruction(current_agent)
        else:
            return self._general_instruction(current_agent)

    def _general_instruction(self, current_agent: dict) -> str:
        """Generic orchestration instruction for any domain."""
        return f"""
    You are an expert AI Orchestrator. Your primary responsibility is to intelligently interpret user requests, break them down into a logical plan of discrete actions, and delegate each action to the most appropriate specialized remote agent using the send_message function.

    **Core Directives & Decision Making:**

    *   **Understand User Intent & Complexity:**
        *   Carefully analyze the user's request to determine the core task(s) they want to achieve.
        *   Identify if the request requires a single agent or a sequence of actions from multiple agents.
        *   Recognize the domain context and terminology relevant to available agents.

    *   **Task Planning & Sequencing:**
        *   Before delegating, outline the clear sequence of tasks.
        *   Identify dependencies between tasks and execute them in the appropriate order.
        *   Agent Reusability: An agent's completion of one task does not make it unavailable.

    *   **Task Delegation & Management:**
        *   Use `send_message` to assign actionable tasks to the selected remote agent.
        *   Include the agent name and all necessary parameters from the user's input.
        *   Provide relevant context from the conversation history when needed.
        *   For sequential tasks, gather outputs from previous steps.

    **Critical Success Verification:**

    *   You **MUST** wait for the tool_output after every send_message call before proceeding.
    *   Base decisions to proceed on explicit confirmation of success from tool_output.
    *   If an operation fails or returns ambiguous results, stop and report the issue.

    **Communication with User:**

    *   Present complete and detailed responses from remote agents.
    *   Clearly inform users which agent is handling their request.
    *   For multi-step operations, explain the planned sequence.

    Available Agents:
    {self.agents}

    Current active agent: {current_agent["active_agent"]}
    """

    def _security_instruction(self, current_agent: dict) -> str:
        """Security-specific orchestration instruction."""
        return f"""
    You are an expert AI Orchestrator for security operations. Your primary responsibility is to intelligently interpret user requests related to cybersecurity, vulnerability management, and bug bounty operations, then delegate tasks to the most appropriate specialized remote agent.

    **Core Directives & Decision Making:**

    *   **Understand Security Context & Complexity:**
        *   Carefully analyze security-related requests to determine core tasks.
        *   Identify if requests require single or multiple agents in sequence.
        *   Recognize security terminology: vulnerabilities, exploits, bug bounties, IOCs, CVEs.

    *   **Task Planning & Sequencing:**
        *   Outline clear sequences of security tasks.
        *   Identify dependencies (e.g., threat analysis may require data from other sources first).
        *   Security Agent Reusability: Call the same agent multiple times for related tasks.

    *   **Task Delegation & Management:**
        *   Use `send_message` to assign security tasks to selected agents.
        *   Include agent name and all necessary security parameters.
        *   Provide security context and threat data as needed.
        *   Execute sequential security operations with proper data flow.

    **Critical Success Verification:**

    *   Wait for tool_output after every send_message call.
    *   Base next steps on explicit success confirmation.
    *   Stop on failures and report exact security issues.

    **Communication with User:**

    *   Present complete security findings without summarization.
    *   Inform users which security agent handles their request.
    *   Explain multi-step security operation sequences.

    **Security Guidelines:**

    *   **Intigriti Agent:** Bug bounty programs, vulnerability submissions, rewards, platform management.
    *   **Cyber Intelligence Agent:** Threat analysis, IOC analysis, vulnerability assessment.
    *   **Cross-Agent Workflows:** Intigriti data → CyberIntel analysis, coordinated monitoring.

    Available Security Agents:
    {self.agents}

    Current active agent: {current_agent["active_agent"]}
    """

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Send a message to an agent with retry logic and circuit breaker protection."""
        if agent_name not in self.remote_agent_connections:
            log.error(
                f"LLM tried to call '{agent_name}' but it was not found. Available agents: {list(self.remote_agent_connections.keys())}"
            )
            raise ValueError(f"Agent \"{agent_name}\" not found.")

        # Check circuit breaker
        if hasattr(self, '_circuit_breaker') and self._circuit_breaker.is_open(agent_name):
            raise ValueError(f"Agent {agent_name} is currently unavailable (circuit breaker open)")

        return await self._send_message_with_retry(agent_name, task, tool_context)

    async def _send_message_with_retry(self, agent_name: str, task: str, tool_context: ToolContext, max_retries: int = 3):
        """Send message with exponential backoff retry logic."""
        start_time = time.time()

        state = tool_context.state
        state["active_agent"] = agent_name
        client = self.remote_agent_connections[agent_name]

        task_id = state.get("task_id", str(uuid.uuid4()))
        context_id = state.get("context_id", str(uuid.uuid4()))
        message_id = state.get("input_message_metadata", {}).get(
            "message_id", str(uuid.uuid4())
        )

        payload = create_send_message_payload(task, task_id, context_id)
        payload["message"]["messageId"] = message_id

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )

        for attempt in range(max_retries + 1):
            try:
                send_response: SendMessageResponse = await client.send_message(
                    message_request=message_request
                )

                if isinstance(send_response.root, SendMessageSuccessResponse) and isinstance(send_response.root.result, Task):
                    # Record success metrics
                    response_time = time.time() - start_time
                    self._metrics.record_message(agent_name)
                    self._metrics.record_response_time(response_time)
                    self._circuit_breaker.record_success(agent_name)
                    return send_response.root.result
                else:
                    raise ValueError("Invalid response format from agent")

            except Exception as e:
                # Record failure metrics
                self._metrics.record_error(agent_name)
                self._circuit_breaker.record_failure(agent_name)

                if attempt == max_retries:
                    log.error(f"Failed to send message to {agent_name} after {max_retries + 1} attempts: {e}")
                    raise

                # Exponential backoff: wait 2^attempt seconds
                wait_time = 2 ** attempt
                if DIAGNOSTIC_MODE:
                    log.warning(f"Attempt {attempt + 1} failed for {agent_name}, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

        return None

    def check_active_agent(self, context: ReadonlyContext):
        state = context.state
        if (
            "session_active" in state
            and state["session_active"]
            and "active_agent" in state
        ):
            return {"active_agent": f"{state['active_agent']}"}
        return {"active_agent": "None"}

    def list_remote_agents(self):
        if not self.cards:
            return []
        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {"name": card.name, "description": card.description}
            )
        return remote_agent_info

    def get_metrics(self) -> dict[str, Any]:
        """Get current orchestration metrics."""
        return self._metrics.get_stats()

    async def get_health_status(self) -> dict[str, bool]:
        """Get health status of all agents."""
        return await self._perform_health_checks()

    def create_agent(self) -> Agent:
        """Synchronously creates the ADK Agent object."""
        return Agent(
            model="gemini-2.5-flash",
            name="orchestrate_agent",
            instruction=self.root_instruction,
            before_agent_callback=self.before_agent_callback,
            description=("Orchestrates tasks for child agents."),
            tools=[self.send_message],
        )


# --- Top-Level Execution ---

log.info("Module-level code is running. Creating uninitialized agent object...")
host_agent_singleton = HostAgent()
root_agent = host_agent_singleton.create_agent()
log.info("Module-level setup finished. 'root_agent' is populated.")
