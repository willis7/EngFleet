import os

import requests
from dotenv import load_dotenv


load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_org_repos(org: str) -> list:
    """Get list of repositories for an organization."""
    url = f"https://api.github.com/orgs/{org}/repos"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        repos = response.json()
        return [repo["name"] for repo in repos]
    else:
        return []


def get_security_advisories(org: str, repo: str) -> list:
    """Get security advisories for a repository."""
    url = f"https://api.github.com/repos/{org}/{repo}/security-advisories"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        return []


def get_dependabot_alerts(org: str, repo: str) -> list:
    """Get Dependabot alerts for a repository."""
    url = f"https://api.github.com/repos/{org}/{repo}/dependabot/alerts"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        return []


def get_code_scanning_alerts(org: str, repo: str) -> list:
    """Get code scanning alerts for a repository."""
    url = f"https://api.github.com/repos/{org}/{repo}/code-scanning/alerts"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        return []


def get_secret_scanning_alerts(org: str, repo: str) -> list:
    """Get secret scanning alerts for a repository."""
    url = f"https://api.github.com/repos/{org}/{repo}/secret-scanning/alerts"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        return []
