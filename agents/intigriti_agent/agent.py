import poml
from google.adk.agents import Agent

from .intigriti_connector_tool import intigriti_toolset


root_agent = Agent(
    name="intigriti_interacting_agent",
    model="gemini-2.0-flash",
    description="An agent that can interact with the Intigriti platform using its API.",
    instruction=poml.poml("prompts/intigriti_agent_instruction.poml")[0]["content"],
    tools=[intigriti_toolset],
)
