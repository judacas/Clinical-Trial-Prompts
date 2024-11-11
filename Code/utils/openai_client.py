# utils/openai_client.py

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


def get_openai_client() -> OpenAI:
    """
    Initializes and returns an OpenAI client.

    Returns:
        OpenAI: The OpenAI client.

    Raises:
        ValueError: If the API key is not found.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        raise ValueError("OPENAI_API_KEY not found in environment variables.")
    logger.info("OpenAI client initialized.")
    return OpenAI(api_key=api_key)
