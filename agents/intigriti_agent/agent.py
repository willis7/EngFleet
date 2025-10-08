from google.adk.agents import Agent

from .intigriti_connector_tool import intigriti_toolset 

root_agent = Agent(
    name="intigriti_interacting_agent",
    model="gemini-2.0-flash",
    description="An agent that can interact with the Intigriti platform using its API.",
    instruction="""
You are an agent that can interact with the Intigriti platform using its API.
You have access to the Intigriti API through the provided OpenAPI toolset.
Use the tools to perform actions on the Intigriti platform as needed.
""",
    tools=[intigriti_toolset],
)