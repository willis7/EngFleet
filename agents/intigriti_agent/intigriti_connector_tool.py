import os

from dotenv import load_dotenv
from fastapi.openapi.models import OAuth2
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.openapi.models import OAuthFlows

from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.auth import AuthCredential
from google.adk.auth import AuthCredentialTypes
from google.adk.auth import OAuth2Auth

load_dotenv()

INTIGRITI_CLIENT_ID = os.getenv("INTIGRITI_CLIENT_ID")
INTIGRITI_CLIENT_SECRET = os.getenv("INTIGRITI_CLIENT_SECRET")
AGENT_REDIRECT_URI = os.getenv("AGENT_REDIRECT_URI")

oauth2_scheme = OAuth2(
    flows=OAuthFlows(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl="https://login.intigriti.com/connect/authorize",
            tokenUrl="https://login.intigriti.com/connect/token",
            scopes={
                "company_external_api": "Gives permission to call the external api",
                "core_platform:read": "Gives read permissions for the core platform endpoints",
                "reward_system:read": "Gives read permissions for the reward system endpoints",
                "offline_access": "Gives permission to retrieve a refresh token",
            },
        )
    )
)

oauth2_credential = AuthCredential(
  auth_type=AuthCredentialTypes.OAUTH2,
  oauth2=OAuth2Auth(
    client_id=INTIGRITI_CLIENT_ID,
    client_secret=INTIGRITI_CLIENT_SECRET,
    redirect_uri=AGENT_REDIRECT_URI
  )
)

intigriti_spec_path = os.path.join(
    os.path.dirname(__file__), "intigriti_swagger_v2_1.json"
)
with open(intigriti_spec_path, "r", encoding="utf-8") as f:
    intigriti_spec_str = f.read()

intigriti_toolset = OpenAPIToolset(
    spec_str=intigriti_spec_str,
    spec_str_type="json",
    auth_scheme=oauth2_scheme,
    auth_credential=oauth2_credential,
)
