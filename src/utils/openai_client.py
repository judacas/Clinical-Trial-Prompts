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

import json
import logging
import os
import threading
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from .config import MAX_CONCURRENT_OPENAI_CALLS

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


openAI_client = get_openai_client()


openai_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
openai_token_usage_lock = threading.Lock()
openai_concurrency_semaphore = threading.Semaphore(MAX_CONCURRENT_OPENAI_CALLS)


def tracked_openai_completion_call(
    *, model, messages, temperature, response_format, timeout
):
    """
    Wrapper for OpenAI completion calls that tracks and prints running token usage,
    including cached input tokens if available.
    """
    with openai_concurrency_semaphore:
        completion = openAI_client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format=response_format,
            timeout=timeout,
        )
        logger.debug(f"OpenAI Completion: {completion}")
        if usage := getattr(completion, "usage", None):
            with openai_token_usage_lock:
                openai_token_usage["prompt_tokens"] += getattr(
                    usage, "prompt_tokens", 0
                )
                openai_token_usage["completion_tokens"] += getattr(
                    usage, "completion_tokens", 0
                )
                openai_token_usage["total_tokens"] += getattr(usage, "total_tokens", 0)
                # Check for cached tokens
                cached_tokens = None
                prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
                if prompt_tokens_details:
                    if hasattr(prompt_tokens_details, "cached_tokens"):
                        cached_tokens = getattr(
                            prompt_tokens_details, "cached_tokens", None
                        )
                    elif isinstance(prompt_tokens_details, dict):
                        cached_tokens = prompt_tokens_details.get("cached_tokens")
                if cached_tokens is not None:
                    openai_token_usage["cached_prompt_tokens"] = (
                        openai_token_usage.get("cached_prompt_tokens", 0)
                        + cached_tokens
                    )
                    logger.info(
                        f"[OpenAI Token Usage] Prompt: {openai_token_usage['prompt_tokens']} | "
                        f"Completion: {openai_token_usage['completion_tokens']} | "
                        f"Total: {openai_token_usage['total_tokens']} | "
                        f"Cached Prompt: {openai_token_usage['cached_prompt_tokens']}"
                    )
                else:
                    logger.info(
                        f"[OpenAI Token Usage] Prompt: {openai_token_usage['prompt_tokens']} | "
                        f"Completion: {openai_token_usage['completion_tokens']} | "
                        f"Total: {openai_token_usage['total_tokens']}"
                    )
        else:
            logger.warning("No token usage information available in the response.")
        return completion


def save_openai_token_usage(output_dir: str):
    """
    Save the OpenAI token usage statistics to a JSON file in output/tokens/ with a timestamped filename.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"openai_token_usage_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        json.dump(openai_token_usage, f, indent=2)
    logger.info(f"OpenAI token usage saved to {filepath}")
