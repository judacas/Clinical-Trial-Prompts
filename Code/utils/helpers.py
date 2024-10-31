# utils/helpers.py

import requests
import os
import logging
from typing import Any, List
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

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


def save_pydantic_model(model: Any, folder: str, file_name: str) -> bool:
    """
    Saves a Pydantic model to a JSON file.

    Args:
        model (Any): The Pydantic model to save.
        folder (str): The folder to save the file in.
        file_name (str): The name of the file.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    logger.info("Saving model to %s", os.path.join(folder, file_name))
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, file_name), 'w', encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=4, serialize_as_any=True))
        logger.info("Model saved successfully.")
        return True
    except Exception as e:
        logger.error("Error saving model: %s", e)
        return False


def get_valid_input(
    question: str, valid_answers: List[str], print_options: bool = False
) -> str:
    """
    Prompts the user for input until a valid answer is given.

    Args:
        question (str): The question to ask.
        valid_answers (List[str]): List of valid answers.
        print_options (bool): Whether to print the valid options.

    Returns:
        str: The valid user input.
    """
    if print_options:
        question += f" ({'/'.join(valid_answers)})"
    completer = WordCompleter(valid_answers, ignore_case=True)
    while True:
        answer = prompt(question + ": ", completer=completer)
        if answer.lower() in (v.lower() for v in valid_answers):
            return answer
        else:
            logger.warning("Invalid input: %s", answer)
            print(f"Please enter one of the valid options: {valid_answers}")
