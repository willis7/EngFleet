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

from intigriti_agent import agent
from intigriti_agent.agent_executor import IntigritiAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host = os.environ.get("A2A_HOST", "localhost")
port = int(os.environ.get("A2A_PORT", 10004))  # Different port from cyber_intel
PUBLIC_URL = os.environ.get("PUBLIC_URL")


class IntigritiAgent:
    """An agent to interact with the Intigriti bug bounty platform."""

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
            id="intigriti_interaction",
            name="Intigriti Platform Interaction",
            description="""
            This agent interacts with the Intigriti bug bounty platform to manage programs,
            submissions, vulnerabilities, and rewards.
            """,
            tags=["bug bounty", "vulnerability management", "intigriti", "security"],
            examples=[
                "List all my active bug bounty programs on Intigriti",
                "Show me recent vulnerability submissions",
                "Get details about program XYZ",
            ],
        )
        self.agent_card = AgentCard(
            name="Intigriti Platform Agent",
            description="""
            This agent interacts with the Intigriti bug bounty platform using its API.
            It can retrieve information about programs, submissions, vulnerabilities,
            rewards, and other platform data. The agent provides a conversational
            interface to the Intigriti platform's capabilities.
            """,
            url=f"{PUBLIC_URL}",
            version="1.0.0",
            defaultInputModes=IntigritiAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=IntigritiAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

    def get_processing_message(self) -> str:
        return "Querying the Intigriti platform..."

    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the Intigriti agent."""
        return agent.root_agent


if __name__ == "__main__":
    try:
        intigritiAgent = IntigritiAgent()

        request_handler = DefaultRequestHandler(
            agent_executor=IntigritiAgentExecutor(
                intigritiAgent.runner, intigritiAgent.agent_card
            ),
            task_store=InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(
            agent_card=intigritiAgent.agent_card,
            http_handler=request_handler,
        )
        logger.info(
            f"Attempting to start server with Agent Card: {intigritiAgent.agent_card.name}"
        )
        logger.info(f"Server object created: {server}")

        uvicorn.run(server.build(), host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)
