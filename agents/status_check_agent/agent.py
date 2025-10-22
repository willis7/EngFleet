import poml
from google.adk.agents import Agent

# Import the tools
from .tools import (
    analyze_status_results,
    check_multiple_websites,
    check_status_page,
    check_website_status,
)


root_agent = Agent(
    name="status_check_agent",
    model="gemini-2.0-flash",
    description="Agent responsible for checking website status pages and determining service operational status",
    instruction=poml.poml("prompts/status_check_agent_instruction.poml")[0]["content"],
    tools=[
        check_website_status,
        check_multiple_websites,
        check_status_page,
        analyze_status_results,
    ],
)
