# services/trial_manager.py
"""
Clinical Trial Data Management Service

This module is responsible for retrieving, processing, and managing clinical trial data.
It handles fetching trial data from ClinicalTrials.gov, identifying and structuring criteria,
and persisting the processed data.

The trial management process follows these steps:
1. Fetch raw trial data from ClinicalTrials.gov API
2. Extract and normalize inclusion, exclusion, and miscellaneous criteria
3. Process trial data through identification and logical structuring pipelines
4. Store the processed data as JSON files

Functions:
    get_extra_criteria: Extract additional criteria from the eligibility module.
    convert_std_ages_to_numerical_ages: Convert standardized age groups to numerical ranges.
    get_trial_data: Retrieve raw trial data from ClinicalTrials.gov API.
    remove_pesky_slash: Clean backslashes from text content.
    process_trial: Process a trial through the entire pipeline.
"""

import logging
import os
import re

import rich

from src.models.identified_criteria import IdentifiedTrial, RawTrialData
from src.models.logical_criteria import LogicalTrial
from src.repositories.trial_repository import export_pydantic_to_json
from src.services.identifier import identify_criterions_from_rawTrial
from src.services.logical_structurizer import logically_structurize_trial
from src.utils.config import DEFAULT_OUTPUT_DIR
from src.utils.helpers import curl_with_status_check

# Configure logging
logger = logging.getLogger(__name__)


def remove_pesky_slash(text: str) -> str:
    """
    Remove backslashes from text to normalize the content.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned text without backslashes.
    """
    return re.sub(r"\\", "", text)


def get_extra_criteria(eligibility_module: dict) -> list[str]:
    """
    Process the eligibility module to extract additional criteria.

    Args:
        eligibility_module (dict): The eligibility module dictionary from ClinicalTrials.gov.

    Returns:
        list[str]: A list of additional criteria extracted from the eligibility module.
    """
    criteria: list[str] = []

    # Extract key eligibility fields
    healthy_volunteers = eligibility_module.get("healthyVolunteers")
    sex = eligibility_module.get("sex")
    minimum_age = eligibility_module.get("minimumAge")
    maximum_age = eligibility_module.get("maximumAge")
    std_ages = eligibility_module.get("stdAges")

    # Process healthy volunteers information
    if healthy_volunteers is not None:
        if healthy_volunteers == "false":
            criteria.append("No healthy volunteers allowed")
        else:
            criteria.append("Healthy volunteers allowed")

    # Process sex requirements
    if sex is not None and sex != "ALL":
        criteria.append(f"Must be {sex}")

    # Process age requirements
    if minimum_age is not None:
        criteria.append(f"Must have minimum age of {minimum_age}")

    if maximum_age is not None:
        criteria.append(f"Must have maximum age of {maximum_age}")

    # Handle standardized age groups if specific age limits aren't provided
    if std_ages and not minimum_age and not maximum_age:
        convert_std_ages_to_numerical_ages(std_ages, criteria)

    return criteria


def convert_std_ages_to_numerical_ages(std_ages: list, criteria: list[str]) -> None:
    """
    Convert standardized age groups to numerical age ranges and add to criteria.

    Args:
        std_ages (list): List of standardized age groups from ClinicalTrials.gov.
        criteria (list[str]): List to append the converted age criteria to.
    """
    min_age = 100
    max_age = 0

    # Define age group mappings
    age_groups = {"CHILD": (0, 17), "ADULT": (18, 64), "OLDER_ADULT": (65, 100)}

    # Determine the minimum and maximum ages based on std_ages
    for age_group in std_ages:
        if age_group in age_groups:
            min_age = min(min_age, age_groups[age_group][0])
            max_age = max(max_age, age_groups[age_group][1])

    # Add age criteria if they are restrictive
    if min_age != 0:
        criteria.append(f"Must be {min_age} or older")
    if max_age != 100:
        criteria.append(f"Must be {max_age} or younger")


def get_trial_data(nct_id: str) -> RawTrialData:
    """
    Retrieve trial data from ClinicalTrials.gov API and format it for processing.

    Args:
        nct_id (str): The NCT ID of the clinical trial.

    Returns:
        RawTrialData: Structured raw trial data.

    Raises:
        ValueError: If the trial data cannot be retrieved or processed.
    """
    logger.info("Fetching trial data for NCT ID: %s", nct_id)
    try:
        # Request data from ClinicalTrials.gov API
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}?fields=NCTId,OfficialTitle,EligibilityModule"
        data = curl_with_status_check(url)

        # Extract study data from the response
        study = data.get("studies", [{}])[0]
        if not study:
            study = data.get("protocolSection", None)
            if not study:
                logger.error("No data found for NCT ID: %s", nct_id)
                logger.debug("Response data: %s", data)
                raise ValueError(f"No data found for NCT ID: {nct_id}")

        # Extract key fields from the study data
        official_title = study.get("identificationModule", {}).get("officialTitle", "")
        eligibility_module = study.get("eligibilityModule", {})
        eligibility = remove_pesky_slash(
            eligibility_module.get("eligibilityCriteria", "")
        )
        extra_criteria = "\n".join(get_extra_criteria(eligibility_module))

        # Split the eligibility text into sections
        inclusion_pos = eligibility.find("Inclusion Criteria:")
        exclusion_pos = eligibility.find("Exclusion Criteria:")

        # Process the eligibility text based on the presence of section markers
        if inclusion_pos != -1 and exclusion_pos != -1:
            inclusion_text = eligibility[
                inclusion_pos + len("Inclusion Criteria:") : exclusion_pos
            ].strip()
            exclusion_text = eligibility[
                exclusion_pos + len("Exclusion Criteria:") :
            ].strip()
            miscellaneous_text = eligibility[:inclusion_pos].strip()

        elif inclusion_pos != -1:
            inclusion_text = eligibility[
                inclusion_pos + len("Inclusion Criteria:") :
            ].strip()
            exclusion_text = ""
            miscellaneous_text = eligibility[:inclusion_pos].strip()
        elif exclusion_pos != -1:
            inclusion_text = ""
            exclusion_text = eligibility[
                exclusion_pos + len("Exclusion Criteria:") :
            ].strip()
            miscellaneous_text = eligibility[:exclusion_pos].strip()
        else:
            inclusion_text = ""
            exclusion_text = ""
            miscellaneous_text = eligibility.strip()

        # Add extra criteria to inclusion criteria
        inclusion_text = (inclusion_text + "\n" + extra_criteria).strip()

        # Create the raw trial data object
        raw_data = RawTrialData(
            nct_id=nct_id,
            official_title=official_title,
            inclusion_criteria=inclusion_text,
            exclusion_criteria=exclusion_text,
            miscellaneous_criteria=miscellaneous_text,
        )

        logger.info("Successfully retrieved trial data.")
        logger.debug("Fully raw input: %s", data)
        logger.debug("Trial data: %s", raw_data)
        return raw_data

    except Exception as e:
        logger.error("Error fetching trial data: %s", e)
        raise ValueError(f"Error fetching trial data: {e}") from e


def process_trial(nct_id: str, folder: str = DEFAULT_OUTPUT_DIR) -> LogicalTrial:
    """
    Process a clinical trial through the complete identification and structuring pipeline.

    Args:
        nct_id (str): The NCT ID of the clinical trial.
        folder (str, optional): The output directory for storing results. Defaults to DEFAULT_OUTPUT_DIR.

    Returns:
        LogicalTrial: The trial data with criteria identified and logically structured.

    Raises:
        ValueError: If trial data processing fails at any stage.
    """
    logger.info("Starting processing for trial NCT ID: %s", nct_id)

    # Fetch raw trial data
    raw_data = get_trial_data(nct_id)
    if not raw_data:
        raise ValueError(f"Failed to fetch trial data for NCT ID: {nct_id}")

    # Identify atomic criteria from the raw trial data
    identified_trial: IdentifiedTrial = identify_criterions_from_rawTrial(raw_data)
    if logger.level <= logging.DEBUG:
        rich.print(
            identified_trial
        )  # Using rich.print for better readability in debug mode

    # Save the identified trial data
    export_pydantic_to_json(
        identified_trial,
        f"{nct_id}_identified.json",
        os.path.join(folder, "identified"),
    )

    # Structure the identified criteria into logical relationships
    logical_trial = logically_structurize_trial(identified_trial)
    if logger.level <= logging.DEBUG:
        rich.print(
            logical_trial
        )  # Using rich.print for better readability in debug mode

    # Save the logical trial data
    export_pydantic_to_json(
        logical_trial, f"{nct_id}_logical.json", os.path.join(folder, "logical")
    )

    logger.info("Trial processing complete for NCT ID: %s", nct_id)

    return logical_trial
