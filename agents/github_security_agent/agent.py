import os

import poml
from google.adk.agents import Agent

from .tools import (
    get_code_scanning_alerts,
    get_dependabot_alerts,
    get_org_repos,
    get_secret_scanning_alerts,
    get_security_advisories,
)


instruction_path = os.path.join(
    os.path.dirname(__file__), "prompts/github_security_instruction.poml"
)

root_agent = Agent(
    name="github_security_agent",
    model="gemini-2.0-flash",
    description="Agent for retrieving and analyzing organization's security position from GitHub",
    instruction=poml.poml(instruction_path)[0]["content"],
    tools=[
        get_org_repos,
        get_security_advisories,
        get_dependabot_alerts,
        get_code_scanning_alerts,
        get_secret_scanning_alerts,
    ],
)
