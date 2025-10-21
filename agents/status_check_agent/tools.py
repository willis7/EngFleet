import logging
import time
from typing import Any

import requests


logger = logging.getLogger(__name__)


def check_website_status(url: str, timeout: int = 10) -> dict[str, Any]:
    """
    Check the status of a website by making an HTTP request.

    Args:
        url: The URL to check
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dict containing status information including:
        - status_code: HTTP status code
        - response_time: Response time in seconds
        - is_operational: Boolean indicating if service appears operational
        - error: Error message if any
    """
    start_time = time.time()

    try:
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        response = requests.get(url, timeout=timeout, allow_redirects=True)
        response_time = time.time() - start_time

        # Consider operational if status code is 2xx or 3xx
        is_operational = 200 <= response.status_code < 400

        return {
            "url": url,
            "status_code": response.status_code,
            "response_time": round(response_time, 2),
            "is_operational": is_operational,
            "error": None,
            "content_length": len(response.content) if response.content else 0,
            "final_url": response.url if response.url != url else None,
        }

    except requests.exceptions.Timeout:
        response_time = time.time() - start_time
        return {
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 2),
            "is_operational": False,
            "error": "Request timeout",
            "content_length": 0,
            "final_url": None,
        }

    except requests.exceptions.ConnectionError:
        response_time = time.time() - start_time
        return {
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 2),
            "is_operational": False,
            "error": "Connection failed",
            "content_length": 0,
            "final_url": None,
        }

    except Exception as e:
        response_time = time.time() - start_time
        return {
            "url": url,
            "status_code": None,
            "response_time": round(response_time, 2),
            "is_operational": False,
            "error": str(e),
            "content_length": 0,
            "final_url": None,
        }


def check_multiple_websites(urls: list[str], timeout: int = 10) -> list[dict[str, Any]]:
    """
    Check the status of multiple websites.

    Args:
        urls: List of URLs to check
        timeout: Request timeout in seconds (default: 10)

    Returns:
        List of status dictionaries for each URL
    """
    results = []
    for url in urls:
        result = check_website_status(url, timeout)
        results.append(result)
        logger.info(
            f"Checked {url}: {'Operational' if result['is_operational'] else 'Down'}"
        )

    return results


def check_status_page(
    url: str, expected_content: str = "", timeout: int = 10
) -> dict[str, Any]:
    """
    Check a status page and optionally validate expected content.

    Args:
        url: The status page URL to check
        expected_content: Text that should be present for the service to be considered operational (empty string to skip)
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dict containing status information
    """
    result = check_website_status(url, timeout)

    if expected_content and result["is_operational"]:
        try:
            # Make another request to check content
            response = requests.get(url, timeout=timeout)
            content_check = expected_content.lower() in response.text.lower()
            result["content_check_passed"] = content_check
            result["expected_content_found"] = content_check
            if not content_check:
                result["is_operational"] = False
                result["error"] = f'Expected content "{expected_content}" not found'
        except Exception as e:
            result["content_check_passed"] = False
            result["expected_content_found"] = False
            result["is_operational"] = False
            result["error"] = f"Content check failed: {e!s}"
    else:
        result["content_check_passed"] = None
        result["expected_content_found"] = None

    return result


def analyze_status_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze status check results and provide summary statistics.

    Args:
        results: List of status check result dictionaries

    Returns:
        Dict containing analysis summary
    """
    total_checks = len(results)
    operational_count = sum(1 for r in results if r["is_operational"])
    down_count = total_checks - operational_count

    avg_response_time = 0
    response_times = [
        r["response_time"] for r in results if r["response_time"] is not None
    ]
    if response_times:
        avg_response_time = round(sum(response_times) / len(response_times), 2)

    errors = [r["error"] for r in results if r["error"]]

    return {
        "total_services": total_checks,
        "operational_services": operational_count,
        "down_services": down_count,
        "overall_status": "All Operational"
        if operational_count == total_checks
        else f"{operational_count}/{total_checks} Operational",
        "average_response_time": avg_response_time,
        "errors": errors,
        "details": results,
    }
