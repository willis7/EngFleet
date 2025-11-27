# GitHub Security Position Agent

## Overview

This agent retrieves and analyzes an organization's security position from GitHub repositories. It gathers data on security advisories, Dependabot alerts, code scanning alerts, and secret scanning alerts to provide a comprehensive security posture report.

## Agent Details

| Attribute | Detail |
|---|---|
| Interaction Type | Conversational |
| Complexity | Easy |
| Agent Type | Single Agent |
| Components | Tools, GitHub API |
| Vertical | Security |

## Setup and Installation

### Prerequisites

- Python 3.12+
- GitHub Personal Access Token with appropriate permissions (read access to org repos, security alerts)

### Installation

1. Clone the repository and navigate to the agent directory.

2. Install dependencies:

   ```bash
   uv sync
   ```

3. Configure environment variables:

   Create a `.env` file with:

   ```
   GITHUB_TOKEN=your_github_token_here
   ```

## Running the Agent Locally

Run the agent using the ADK CLI:

```bash
cd agents/github-security-agent
adk run github_security_agent
```

Or from the ADK web UI:

```bash
adk web
```

Then select the `github-security-agent` from the dropdown.

## Example Interaction

**User:**
> Analyze the security position of the google organization

**Agent:**
> [Provides a markdown report summarizing security findings across repositories]</content>
</xai:function_call"> 

<xai:function_call name="write">
<parameter name="filePath">agents/github-security-agent/.env.example