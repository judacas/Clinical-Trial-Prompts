# utils/helpers.py

import requests
import logging

# Configure logging
logger = logging.getLogger(__name__)


def curl_with_status_check(url: str) -> dict:
    """
    Sends a GET request and checks the response status.

    Args:
        url (str): The URL to request.

    Returns:
        dict: The JSON response.

    Raises:
        requests.exceptions.RequestException: If the request fails.
    """
    logger.info("Sending GET request to URL: %s", url)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    logger.info("Request successful.")
    return response.json()