# services/trial_manager.py
import logging
import os

import rich
from models.logical_criteria import LogicalTrial
from repositories.trial_repository import export_pydantic_to_json
from services.logical_structurizer import logically_structurize_trial
from models.identified_criteria import IdentifiedTrial, RawTrialData
from services.identifier import identify_criterions_from_rawTrial
from utils.helpers import curl_with_status_check

import re

def remove_pesky_slash(text: str) -> str:
    return re.sub(r'\\', '', text)

# Configure logging
logger = logging.getLogger(__name__)

def get_extra_criteria(eligibilityModule: dict) -> list[str]:
    """
    Processes the eligibility module to extract additional criteria and returns them as a string.

    Args:
        eligibilityModule (dict): The eligibility module dictionary.

    Returns:
        str: A string with all of the new criteria, one per line.
    """
    criteria: list[str] = []

    # Get the values of the fields
    healthy_volunteers = eligibilityModule.get("healthyVolunteers")
    sex = eligibilityModule.get("sex")
    minimum_age = eligibilityModule.get("minimumAge")
    maximum_age = eligibilityModule.get("maximumAge")
    std_ages = eligibilityModule.get("stdAges")

    if healthy_volunteers is not None:
        if healthy_volunteers == "false":
            criteria.append("No healthy volunteers allowed")
        else:
            criteria.append("Healthy volunteers allowed")

    if sex is not None and sex != "ALL":
        criteria.append(f"Must be {sex}")

    if minimum_age is not None:
        criteria.append(f"Must have minimum age of {minimum_age}")

    if maximum_age is not None:
        criteria.append(f"Must have maximum age of {maximum_age}")

    if std_ages and not minimum_age and not maximum_age:
        convertStdAgesToNumericalAges(std_ages, criteria)
    return criteria

def convertStdAgesToNumericalAges(std_ages, criteria: list[str]):
    minAge = 100
    maxAge = 0

    # Define age group mappings
    age_groups = {
        "CHILD": (0, 17),
        "ADULT": (18, 64),
        "OLDER_ADULT": (65, 100)
    }

    # Determine the minimum and maximum ages based on std_ages
    for age_group in std_ages:
        if age_group in age_groups:
            minAge = min(minAge, age_groups[age_group][0])
            maxAge = max(maxAge, age_groups[age_group][1])

    if minAge != 0:
        criteria.append(f"Must be {minAge} or older")
    if maxAge != 100:
        criteria.append(f"Must be {maxAge} or younger")


def get_trial_data(nct_id: str) -> RawTrialData:
    # sourcery skip: extract-method, hoist-if-from-if
    """
    Retrieves trial data from ClinicalTrials.gov API.

    Args:
        nct_id (str): The NCT ID of the clinical trial.

    Returns:
        Optional[RawTrialData]: The raw trial data or None if failed.
    """
    logger.info("Fetching trial data for NCT ID: %s", nct_id)
    try:
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}?fields=NCTId,OfficialTitle,EligibilityModule"
        data = curl_with_status_check(url)
        study = data.get("studies", [{}])[0]
        if not study:
            study = data.get("protocolSection", None)
            if not study:
                logger.error("No data found for NCT ID: %s", nct_id)
                logger.debug("Response data: %s", data)
                raise ValueError(f"No data found for NCT ID: {nct_id}")


        official_title = study.get(
            "identificationModule", {}
        ).get("officialTitle", "")
        eligibilityModule = study.get("eligibilityModule", {})
        eligibility = remove_pesky_slash(eligibilityModule.get("eligibilityCriteria", ""))
        extra_criteria = "\n".join(get_extra_criteria(eligibilityModule))
        
        inclusion_pos = eligibility.find("Inclusion Criteria:")
        exclusion_pos = eligibility.find("Exclusion Criteria:")

        # Separate the text into inclusion, exclusion, and miscellaneous sections
        if inclusion_pos != -1 and exclusion_pos != -1:
            inclusion_text = eligibility[inclusion_pos + len("Inclusion Criteria:"):exclusion_pos].strip()
            exclusion_text = eligibility[exclusion_pos + len("Exclusion Criteria:"):].strip()
            miscellaneous_text = eligibility[:inclusion_pos].strip()
            
        elif inclusion_pos != -1:
            inclusion_text = eligibility[inclusion_pos + len("Inclusion Criteria:"):].strip()
            exclusion_text = ""
            miscellaneous_text = eligibility[:inclusion_pos].strip()
        elif exclusion_pos != -1:
            inclusion_text = ""
            exclusion_text = eligibility[exclusion_pos + len("Exclusion Criteria:"):].strip()
            miscellaneous_text = eligibility[:exclusion_pos].strip()
        else:
            inclusion_text = ""
            exclusion_text = ""
            miscellaneous_text = eligibility.strip()
            
        inclusion_text = (inclusion_text + "\n" + extra_criteria).strip()
        
        

        raw_data = RawTrialData(
            nct_id=nct_id, official_title=official_title, inclusion_criteria=inclusion_text, exclusion_criteria=exclusion_text, miscellaneous_criteria=miscellaneous_text
        )
        logger.info("Successfully retrieved trial data.")
        logger.debug("Fully raw input: %s", data)
        logger.debug("Trial data: %s", raw_data)
        return raw_data
    except Exception as e:
        logger.error("Error fetching trial data: %s", e)
        raise ValueError(f"Error fetching trial data: {e}") from e


def process_trial(nct_id: str, folder: str = "output") -> LogicalTrial:
    raw_data = get_trial_data(nct_id)
    if not raw_data:
        raise ValueError(f"Failed to fetch trial data for NCT ID: {nct_id}")
    
    identified_trial: IdentifiedTrial = identify_criterions_from_rawTrial(raw_data)
    rich.print(identified_trial)
    export_pydantic_to_json(identified_trial, f"{nct_id}_identified.json", os.path.join(folder, "identified"))
    
    logical_trial = logically_structurize_trial(identified_trial)
    rich.print(logical_trial)
    export_pydantic_to_json(logical_trial, f"{nct_id}_logical.json", os.path.join(folder, "logical"))
    
    logger.info("Trial processing complete for NCT ID: %s", nct_id)
    
    return logical_trial
