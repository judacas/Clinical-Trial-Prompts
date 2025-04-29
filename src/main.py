# main.py
"""
Clinical Trial Processing Application

This module serves as the entry point for the clinical trial processing application.
It provides a command-line interface for selecting and processing clinical trials.

The application can:
1. Process trials specified manually by NCT ID
2. Process all cancer trials from the CHIA dataset
3. Exit the application

Each trial is processed to extract and structure its eligibility criteria.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator

from src.services.trial_manager import process_trial
from src.utils.config import (
    DEFAULT_OUTPUT_DIR,
    MAX_CONCURRENT_OPENAI_CALLS,
    setup_logging,
)
from src.utils.helpers import curl_with_status_check
from src.utils.openai_client import save_openai_token_usage

# Configure application logging
setup_logging(log_to_file=True, log_level=logging.INFO)
output_dir = os.path.join(DEFAULT_OUTPUT_DIR, "recent_us", "avg10")


def getChiaCancerTrials() -> list[str]:
    """
    Retrieve a list of all cancer trial NCT IDs from the CHIA dataset.

    Returns:
        list[str]: List of NCT IDs for cancer trials.
    """
    onlyCancerFolder = os.path.join("..", "Trials", "CHIA", "OnlyCancerTrials")
    return [
        file.split(".")[0]
        for file in os.listdir(onlyCancerFolder)
        if file.endswith(".json")
    ]


def getTrialsFromUser() -> list[str]:
    """
    Prompt the user to enter trial NCT IDs manually.

    Returns:
        list[str]: List of user-specified NCT IDs.
    """
    trials = []
    while nct_id := input(
        "Enter the NCT ID of the trial you want to process (or press Enter to finish): "
    ).strip():
        trials.append(nct_id)
    return trials


def get_all_nct_ids_from_folder(folder_path: str) -> list[str]:
    """
    Retrieve all NCT IDs from the first 11 characters of JSON file names in the specified folder.

    Args:
        folder_path (str): Path to the folder containing JSON files.

    Returns:
        list[str]: List of NCT IDs.
    """
    return [
        file_name[:11]
        for file_name in os.listdir(folder_path)
        if file_name.endswith(".json")
    ]


def getAllCancerTrials(n: int) -> Generator[str, None, None]:
    """
    Retrieve a generator of all cancer trial NCT IDs available in clinicaltrials.gov.

    Yields:
        str: NCT ID for a cancer trial.
    """
    url = f"https://clinicaltrials.gov/api/v2/studies?query.cond=cancer&query.term=cancer&query.titles=Cancer&fields=NCTId&pageSize={n}"

    folder_path = os.path.join(DEFAULT_OUTPUT_DIR, "allTrials", "logical")
    nct_ids = get_all_nct_ids_from_folder(folder_path)
    response = curl_with_status_check(url)
    studies = response.get("studies", [])
    nextToken = response.get("nextPageToken", "")

    while True:
        for study in [
            s
            for s in studies
            if s["protocolSection"]["identificationModule"]["nctId"] not in nct_ids
        ]:
            yield study["protocolSection"]["identificationModule"]["nctId"]

        if not nextToken:
            break

        next_url = f"{url}&pageToken={nextToken}"
        response = curl_with_status_check(next_url)
        studies = response.get("studies", [])
        nextToken = response.get("nextPageToken", "")


def get_trials(n: int = 100) -> list[str] | Generator[str] | None:
    """
    Present options to the user for selecting trials to process.

    Returns:
        list[str] | None: List of NCT IDs to process, or None if user chooses to quit.
    """
    while True:
        user_choice = (
            input(
                "Please choose one of the following\n'm' for manual input\n'c' to process all cancer trials from CHIA\n'a' for all cancer trials\n'q' to quit: "
            )
            .strip()
            .lower()
        )

        if user_choice == "m":
            return getTrialsFromUser()
        elif user_choice == "c":
            return getChiaCancerTrials()
        elif user_choice == "a":
            return getAllCancerTrials(n)
        elif user_choice == "q":
            return None
        else:
            print("Invalid choice. Please try again.")


def process_trial_wrapper(nct_id: str, folder: str):
    """
    Wrapper function to process a trial and handle exceptions.

    Args:
        nct_id (str): NCT ID of the trial to process.
    """
    logger = logging.getLogger(__name__)
    try:
        process_trial(nct_id, folder)
        logger.info(f"Successfully processed trial {nct_id}")
    except Exception as e:
        logger.error(f"Failed to process trial {nct_id}: {str(e)}")


def main():
    """
    Main application function. Handles user interaction and processes selected trials.
    """
    logger = logging.getLogger(__name__)
    logger.info("Application started...")

    trials = get_trials(100)
    if not trials:
        logger.info("No trials selected, exiting...")
        return

    if isinstance(trials, list):
        logger.info(f"Selected {len(trials)} trials for processing")
        logger.info("These are the trials selected: %s", trials)

    # Process each trial in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_OPENAI_CALLS) as executor:
        future_to_nct_id = {
            executor.submit(process_trial_wrapper, nct_id, output_dir): nct_id
            for nct_id in trials
        }
        for future in as_completed(future_to_nct_id):
            nct_id = future_to_nct_id[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error processing trial {nct_id}: {str(e)}")

    logger.info("Processing complete")


if __name__ == "__main__":
    main()
    save_openai_token_usage(output_dir)
