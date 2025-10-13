import asyncio

from dotenv import load_dotenv
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

    query = "Vulnerability exposure assessment (MongoDB/Atlas) TLP:GREEN. Assess risk for MongoDB AtlasHQ SaaS–hosted clusters running MongoDB Server 6.x/7.x. Environment: Multiple internet-facing clusters with public IPs; primary auth is username/password (SCRAM), with some clusters now using Mongo STS/federated access. Data sensitivity: PII. Business criticality: High. Timeframe: last 14 days. Evaluate relevance of current MongoDB Server and MongoDB Atlas platform CVEs (including those in MongoDB Security Bulletins), evidence of exploitation in the wild, and likely exposure paths specific to Atlas public endpoints, Atlas API keys, IP access list configurations, authentication methods (username/password vs STS), TLS posture, and backup/restore pipelines. Provide prioritized defensive actions (Immediate/48h/2+ weeks), hardening guidance tailored to Atlas (network access lists, private endpoints/peering, TLS, SCRAM-SHA-256, SSO/MFA, API key scoping/rotation, auditing, Client-Side Field Level Encryption/Queryable Encryption, snapshot protections), log sources to review, and example detections (Sigma/Splunk/KQL). Include MITRE ATT&CK mapping, risk and confidence ratings, and references (NVD, CISA KEV, MongoDB Security Bulletins, vendor advisories)."
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
