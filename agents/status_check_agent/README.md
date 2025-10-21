# Status Check Agent

A specialized agent for monitoring website status pages and determining service operational status. This agent can check individual websites, monitor multiple services simultaneously, and provide detailed health reports.

## Features

- **Individual Website Checks**: Monitor single websites for availability, response time, and HTTP status codes
- **Bulk Status Monitoring**: Check multiple websites simultaneously with consolidated reports
- **Status Page Validation**: Check dedicated status pages and validate expected content
- **Service Health Analysis**: Analyze results across multiple services with operational summaries
- **Response Time Monitoring**: Track and report response times with performance categorization

## Capabilities

- HTTP status code checking (200-599)
- Response time measurement
- Content validation for status pages
- Bulk monitoring of multiple services
- Detailed health reporting with recommendations

## Usage Examples

- "Check if google.com is operational"
- "Monitor these status pages: https://status.github.com, https://status.cloudflare.com"
- "Check GitHub status page and confirm all systems are operational"
- "Analyze the health of these services: [list of URLs]"

## Setup

1. Copy `.env.example` to `.env` and configure environment variables:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies (from project root):
   ```bash
   uv sync
   ```

3. Start the agent server:
   ```bash
   python a2a_server.py
   ```

## Environment Variables

- `A2A_HOST`: Host for the A2A server (default: localhost)
- `A2A_PORT`: Port for the A2A server (default: 10004)
- `PUBLIC_URL`: Public URL for the agent
- `DEFAULT_TIMEOUT`: Default timeout for status checks in seconds (default: 10)

## Response Format

The agent provides structured status reports including:

- **Service Status Summary**: Total services checked, operational count, average response time
- **Detailed Results**: Individual service status, response times, and issues
- **Recommendations**: Actions needed for failed or degraded services

## Performance Standards

- **< 1 second**: Excellent response time
- **1-3 seconds**: Good response time
- **3-10 seconds**: Acceptable response time
- **> 10 seconds**: Slow/degraded performance

## Status Code Interpretation

- **200-299**: Operational (Success)
- **300-399**: Operational (Redirects)
- **400-499**: Client Error (May indicate service issues)
- **500-599**: Server Error (Service down)
