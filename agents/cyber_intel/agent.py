import poml
from typing import cast, List, Dict, Any
from google.adk.agents import Agent
from google.adk.tools import google_search


root_agent = Agent(
    name="cyber_intel_agent",
    model="gemini-2.0-flash",
    description="Agent tasked with analysing cyber threat inputs and providing actionable, defensive threat intelligence",
    instruction=poml.poml("prompts/cyber_intel_instruction.poml")[0]["content"],
    tools=[google_search],
)
