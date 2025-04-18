# utils/helpers.py
"""
Helper Utilities for Clinical Trial Analysis

This module provides utility functions that support various operations across the
clinical trial analysis application. It includes network communication helpers
and other general-purpose utilities.

Functions:
    curl_with_status_check: Send a GET request and handle response validation.
"""

import logging

import requests

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


def get_non_empty_input(
    prompt: str, empty_message: str = "Input cannot be empty. Please try again."
) -> str:
    """
    Repeatedly prompts the user for input until a non-empty response is provided.

    This function displays a prompt to the user and collects their input. If the user
    provides an empty string (or just whitespace), it displays the specified empty_message
    and prompts again. This continues until a non-empty response is received.

    Args:
        prompt (str): The question or prompt to display to the user.
        empty_message (str): The message to display if the user provides an empty response.
                            Defaults to "Input cannot be empty. Please try again."

    Returns:
        str: The non-empty user input (with leading/trailing whitespace removed).
    """
    while True:
        if user_input := input(prompt).strip():
            if user_input.lower() in ["quit", "exit"]:
                print("Exiting program.")
                import sys

                sys.exit(0)
            return user_input.strip()
        print(empty_message)
