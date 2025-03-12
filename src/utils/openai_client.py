# utils/openai_client.py
"""
OpenAI Client Module for Clinical Trial Analysis

This module manages the initialization and configuration of the OpenAI client
used for LLM-based clinical trial eligibility criteria processing. It handles
API key loading and client setup.

The module ensures:
1. Environment variables are properly loaded
2. API key availability is verified
3. OpenAI client is correctly initialized
4. Errors are appropriately logged and handled

Functions:
    get_openai_client: Initialize and return a configured OpenAI client.
"""

import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


def get_openai_client() -> OpenAI:
    """
    Initialize and return an OpenAI client configured with the appropriate API key.

    This function loads the API key from environment variables and creates a
    properly configured OpenAI client for use throughout the application.

    Returns:
        OpenAI: The initialized OpenAI client.

    Raises:
        ValueError: If the OPENAI_API_KEY is not found in environment variables.
    """
    # Retrieve API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")

    # Verify API key existence
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    logger.info("OpenAI client initialized.")

    # Create and return the OpenAI client
    return OpenAI(api_key=api_key)
