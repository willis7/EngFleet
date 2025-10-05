import json
import os

import requests
from dotenv import load_dotenv


load_dotenv()
BASE_URL = os.environ.get("INTIGRITI_BASE_URL")
API_TOKEN = os.environ.get("INTIGRITI_API_TOKEN")


def get_submissions(
    api_token: str = API_TOKEN,
    program_id: str = None,
    state: str = None,
    severity: str = None,
    page: int = 1,
    limit: int = 50,
    base_url: str = BASE_URL,
):
    """
    Sends a GET request to the Intigriti API to retrieve submission overview.

    Args:
        api_token (str): Your Intigriti API authentication token (Bearer token).
        program_id (str): Filter submissions by specific program ID.
        state (str): Filter by submission state (e.g., 'triage', 'accepted', 'closed').
        severity (str): Filter by severity level (e.g., 'low', 'medium', 'high', 'critical').
        page (int: Page number for pagination. Defaults to 1.
        limit (int): Number of results per page. Defaults to 50.
        base_url (str): The base URL of the Intigriti API. Defaults to INTIGRITI_BASE_URL.

    Returns:
        dict: The JSON response containing submissions data if successful.
              Returns None if an error occurs.

    Raises:
        requests.exceptions.RequestException: If there's an issue with the network request.
    """
    url = f"{base_url}/external/company/v2.1/submissions"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    # Build query parameters
    params = {"page": page, "limit": limit}

    if program_id:
        params["programId"] = program_id
    if state:
        params["state"] = state
    if severity:
        params["severity"] = severity

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print(
            f"Successfully retrieved submissions. Status Code: {response.status_code}"
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving submissions: {e}")
        if hasattr(e.response, "text"):
            print(f"Response text: {e.response.text}")
        return None
    except json.JSONDecodeError:
        print(
            f"Error decoding JSON response from {url}. Response text: {response.text}"
        )
        return None
