import asyncio

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from . import agent


load_dotenv()


async def async_main():
    session_service = InMemorySessionService()

    session = await session_service.create_session(
        state={}, app_name="cyber_intel_app", user_id="user_dc"
    )

    query = "Vulnerability exposure assessment (example) TLP:GREEN. Assess risk for Atlassian Confluence Data Center (8.5.4 and 8.7.x). Two internet-facing nodes show /setup endpoints exposed. Timeframe: last 14 days. Industry: Technology. Business criticality: High. Evaluate relevance of CVE-2023-22515 (and related CVEs), exploitation in the wild, and our likely exposure paths. Provide prioritized defensive actions (Immediate/48h/2+ weeks), hardening guidance, log sources to review, and example detections (Sigma/Splunk/KQL). Include MITRE ATT&CK mapping, risk and confidence ratings, and references (NVD, CISA KEV, vendor advisories)."
    print(f"User Query: '{query}'")
    content = types.Content(role="user", parts=[types.Part(text=query)])

    root_agent = agent.root_agent
    runner = Runner(
        app_name="cyber_intel_app",
        agent=root_agent,
        session_service=session_service,
    )
    print("Running agent...")
    events_async = runner.run_async(
        session_id=session.id, user_id=session.user_id, new_message=content
    )

    async for event in events_async:
        print(f"Event received: {event}")


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except Exception as e:
        print(f"An error occurred: {e}")
