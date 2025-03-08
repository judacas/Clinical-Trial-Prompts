# utils/helpers.py
"""
Helper Utilities for Clinical Trial Analysis

This module provides utility functions that support various operations across the
clinical trial analysis application. It includes network communication helpers
and other general-purpose utilities.

Functions:
    curl_with_status_check: Send a GET request and handle response validation.
"""

import requests
import logging

# Configure logging
logger = logging.getLogger(__name__)


def curl_with_status_check(url: str) -> dict:
    """
    Send a GET request to a URL and check the response status.
    
    This function handles HTTP requests to external APIs, including error checking
    and response validation. It automatically raises exceptions for non-successful
    HTTP responses.

    Args:
        url (str): The URL to send the GET request to.

    Returns:
        dict: The JSON response parsed as a dictionary.

    Raises:
        requests.exceptions.RequestException: If the request fails due to network issues,
            timeout, or non-successful HTTP status code.
    """
    logger.info("Sending GET request to URL: %s", url)
    
    # Send the request with a timeout to prevent hanging
    response = requests.get(url, timeout=10)
    
    # Raise an exception for non-200 status codes
    response.raise_for_status()
    
    logger.info("Request successful.")
    
    # Return the parsed JSON response
    return response.json()