import logging
import os
from typing import ClassVar

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

from status_check_agent import agent
from status_check_agent.agent_executor import StatusCheckAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host = os.environ.get("A2A_HOST", "localhost")
port_str = os.environ.get("A2A_PORT", "10005")
port = int(port_str) if port_str.isdigit() else 10005
PUBLIC_URL = os.environ.get("PUBLIC_URL")


class StatusCheckAgent:
    """An agent to check website status pages and service operational status."""

    SUPPORTED_CONTENT_TYPES: ClassVar[list[str]] = ["text", "text/plain"]

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
            id="status_check",
            name="Status Monitoring",
            description="""
            This agent checks website status pages and determines if services are operational.
            It can monitor HTTP status codes, response times, and validate expected content.
            """,
            tags=["monitoring", "status", "availability", "health-check"],
            examples=[
                "Check if google.com is operational",
                "Monitor these status pages: https://status.github.com, https://status.cloudflare.com",
                "Check GitHub status page and confirm all systems are operational",
            ],
        )
        self.agent_card = AgentCard(
            name="Status Check Agent",
            description="""
            This agent monitors website availability and service operational status. It can check individual websites,
            monitor multiple services simultaneously, validate status pages, and provide detailed health reports
            including response times, HTTP status codes, and content validation.
            """,
            url=f"{PUBLIC_URL}",
            version="1.0.0",
            defaultInputModes=StatusCheckAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=StatusCheckAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

    def get_processing_message(self) -> str:
        return "Checking service status..."

    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the status check agent."""
        return agent.root_agent


if __name__ == "__main__":
    try:
        status_check_agent = StatusCheckAgent()

        request_handler = DefaultRequestHandler(
            agent_executor=StatusCheckAgentExecutor(
                status_check_agent.runner, status_check_agent.agent_card
            ),
            task_store=InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(
            agent_card=status_check_agent.agent_card,
            http_handler=request_handler,
        )
        logger.info(
            f"Attempting to start server with Agent Card: {status_check_agent.agent_card.name}"
        )
        logger.info(f"Server object created: {server}")

        uvicorn.run(server.build(), host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)
