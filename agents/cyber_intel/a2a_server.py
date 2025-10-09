import logging
import os

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from cyber_intel import agent
from cyber_intel.agent_executor import CyberIntelAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host = os.environ.get("A2A_HOST", "localhost")
port = int(os.environ.get("A2A_PORT", 10003))
PUBLIC_URL = os.environ.get("PUBLIC_URL")


class CyberIntelAgent:
    """An agent to help user planning a event with its desire location."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self._agent = self._build_agent()
        self.runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="cyber_intel",
            name="Cyber Intelligence",
            description="""
            This agent analyzes cyber threat inputs and provides actionable, defensive threat intelligence.
            """,
            tags=["cybersecurity", "threat intelligence", "vulnerability assessment"],
            examples=[
                "Analyze the following Indicators of Compromise (IOCs) and provide a threat assessment."
            ],
        )
        self.agent_card = AgentCard(
            name="Cyber Intelligence Agent",
            description="""
            This agent analyzes cyber threat inputs and provides actionable, defensive threat intelligence. It can process various types of cyber threat data, including Indicators of Compromise (IOCs), 
            security telemetry, vulnerabilities, and contextual information.
            """,
            url=f"{PUBLIC_URL}",
            version="1.0.0",
            defaultInputModes=CyberIntelAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=CyberIntelAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

    def get_processing_message(self) -> str:
        return "Processing the cyber threat intelligence request..."

    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the cyber intelligence agent."""
        return agent.root_agent


if __name__ == "__main__":
    try:
        cyberIntelAgent = CyberIntelAgent()

        request_handler = DefaultRequestHandler(
            agent_executor=CyberIntelAgentExecutor(
                cyberIntelAgent.runner, cyberIntelAgent.agent_card
            ),
            task_store=InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(
            agent_card=cyberIntelAgent.agent_card,
            http_handler=request_handler,
        )
        logger.info(
            f"Attempting to start server with Agent Card: {cyberIntelAgent.agent_card.name}"
        )
        logger.info(f"Server object created: {server}")

        uvicorn.run(server.build(), host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)
