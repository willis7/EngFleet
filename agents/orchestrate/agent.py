import asyncio
import json
import os
import uuid
from typing import Any

import httpx
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskState,
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
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext


# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# --- Configuration ---
REMOTE_AGENT_ADDRESSES_STR = os.getenv("REMOTE_AGENT_ADDRESSES", "")
REMOTE_AGENT_ADDRESSES = [
    addr.strip() for addr in REMOTE_AGENT_ADDRESSES_STR.split(",") if addr.strip()
]

log.info(f"Remote Agent Addresses: {REMOTE_AGENT_ADDRESSES}")


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

    async def _initialize(self):
        """
        DIAGNOSTIC VERSION: This method will test each connection one-by-one
        with aggressive logging to force the hidden error to appear.
        """
        if not REMOTE_AGENT_ADDRESSES or not REMOTE_AGENT_ADDRESSES[0]:
            log.error(
                "CRITICAL FAILURE: REMOTE_AGENT_ADDRESSES environment variable is empty. Cannot proceed."
            )
            self.is_initialized = True
            return

        async with httpx.AsyncClient(timeout=30) as client:
            for i, address in enumerate(REMOTE_AGENT_ADDRESSES):
                log.info(f"--- STEP 3.{i}: Attempting connection to: {address} ---")
                try:
                    card_resolver = A2ACardResolver(client, address)
                    card = await card_resolver.get_agent_card()

                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                    log.info(
                        f"--- STEP 5.{i}: Successfully stored connection for {card.name} ---"
                    )

                except Exception as e:
                    log.error(
                        f"--- CRITICAL FAILURE at STEP 4.{i} for address: {address} ---"
                    )
                    log.error(
                        f"--- The hidden exception type is: {type(e).__name__} ---"
                    )
                    log.error(
                        "--- Full exception details and traceback: ---", exc_info=True
                    )

        log.error("STEP 6: Finished attempting all connections.")
        if not self.remote_agent_connections:
            log.error(
                "FINAL VERDICT: The loop finished, but the remote agent list is still empty."
            )
        else:
            agent_info = [
                json.dumps({"name": c.name, "description": c.description})
                for c in self.cards.values()
            ]
            self.agents = "\n".join(agent_info)
            log.info(
                f"--- FINAL SUCCESS: Initialization complete. {len(self.remote_agent_connections)} agents loaded. ---"
            )

        self.is_initialized = True

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
        current_agent = self.check_active_agent(context)
        return f"""
    You are an expert AI Orchestrator for the EngFleet security platform. Your primary responsibility is to intelligently interpret user requests related to cybersecurity, vulnerability management, and bug bounty operations, then delegate tasks to the most appropriate specialized remote agent using the send_message function.

    **Core Directives & Decision Making:**

    *   **Understand Security Context & Complexity:**
        *   Carefully analyze the user's security-related request to determine the core task(s) they want to achieve.
        *   Identify if the request requires a single agent or a sequence of actions from multiple agents. For example, "Check my Intigriti programs and analyze any threats in the submissions" would require both agents in sequence.
        *   Recognize security terminology: vulnerabilities, exploits, bug bounties, threat intelligence, IOCs, CVEs, etc.

    *   **Task Planning & Sequencing (for Multi-Step Security Operations):**
        *   Before delegating, outline the clear sequence of security tasks.
        *   Identify dependencies. If threat analysis requires data from Intigriti first, execute them sequentially.
        *   Security Agent Reusability: An agent's completion of one task does not make it unavailable. You can call the same agent multiple times for different but related security tasks.

    *   **Task Delegation & Management (using `send_message`):**
        *   **Delegation:** Use `send_message` to assign actionable security tasks to the selected remote agent. Your `send_message` call MUST include:
            *   The `agent_name` you've selected (either "Intigriti Platform Agent" or "Cyber Intelligence Agent").
            *   The `task` or all necessary parameters extracted from the user's input, formatted appropriately.
        *   **Security Context for Remote Agents:** If a remote agent needs additional context about security findings, provide relevant details from the conversation history.
        *   **Sequential Security Task Execution:**
            *   After a security analysis completes, gather any necessary threat data or vulnerability information.
            *   Then, use `send_message` for the next agent in the sequence, providing it with relevant security context.
        *   **Active Security Agent Prioritization:** If an agent is already analyzing security data and the user's request is related, route follow-up requests directly to that agent.

    **Critical Success Verification:**

    *   You **MUST** wait for the tool_output after every send_message call before taking any further action.
    *   Your decision to proceed to the next security task **MUST** be based entirely on a confirmation of success from the tool_output.
    *   If a security operation fails, returns an error, or the tool_output is ambiguous, you MUST STOP the sequence and report the exact failure to the user.
    *   DO NOT assume a security task was successful. Only state that a task is complete if the tool's response explicitly confirms success.

    **Communication with User:**

    *   **Transparent Security Reporting:** Always present the complete and detailed security findings from the remote agent to the user. Security data should not be summarized unless explicitly requested.
    *   When you delegate a security task, clearly inform the user which specialized agent is handling it.
    *   For multi-step security operations, inform the user of the planned sequence (e.g., "First I'll check your Intigriti programs, then analyze any security threats in the submissions").
    *   **Security Decision Making:** For security-related confirmations or ambiguous requests, make reasonable security-focused decisions rather than asking for user input.

    **Security-Specific Guidelines:**

    *   **Intigriti Agent:** Use for bug bounty programs, vulnerability submissions, rewards, platform management, researcher interactions.
    *   **Cyber Intelligence Agent:** Use for threat analysis, security research, IOC analysis, vulnerability assessment, threat intelligence gathering.
    *   **Cross-Agent Security Workflows:** Common patterns include:
        - Retrieve vulnerability data from Intigriti → Analyze threats with CyberIntel
        - Get threat intelligence from CyberIntel → Check related programs on Intigriti
        - Monitor both platforms for coordinated security insights

    **Important Security Reminders:**

    *   **Autonomous Security Operations:** Engage with security agents directly without seeking user permission for standard security tasks.
    *   **Focused Security Information:** Provide agents with relevant security context and threat data only.
    *   **Security Tool Reliance:** Use your available security tools primarily. For insufficient security information, request clarification from the user.
    *   **Prioritize Recent Security Events:** Focus on the most recent security findings while maintaining awareness of ongoing security operations.
    *   Always select the correct security agent based on their specialized security capabilities.

    Available Security Agents:
    {self.agents}

    Current active agent: {current_agent["active_agent"]}
    """

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        if agent_name not in self.remote_agent_connections:
            log.error(
                f"LLM tried to call '{agent_name}' but it was not found. Available agents: {list(self.remote_agent_connections.keys())}"
            )
            raise ValueError(f"Agent '{agent_name}' not found.")

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

        send_response: SendMessageResponse = await client.send_message(
            message_request=message_request
        )

        if not isinstance(
            send_response.root, SendMessageSuccessResponse
        ) or not isinstance(send_response.root.result, Task):
            return None
        return send_response.root.result

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
