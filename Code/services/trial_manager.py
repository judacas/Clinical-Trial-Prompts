# services/trial_manager.py
import logging
from models.identified_criteria import IdentifiedTrial, RawTrialData
from services.identifier import identify_line_by_line
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

    inclusion_index = None
    exclusion_index = None


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
        extra_criteria = get_extra_criteria(eligibilityModule)
        eligibility += "\n" + "\n".join(extra_criteria)   
        
        

        raw_data = RawTrialData(
            nct_id=nct_id, official_title=official_title, criteria=eligibility
        )
        logger.info("Successfully retrieved trial data.")
        logger.debug("Fully raw input: %s", data)
        logger.debug("Trial data: %s", raw_data)
        return raw_data
    except Exception as e:
        logger.error("Error fetching trial data: %s", e)
        raise ValueError(f"Error fetching trial data: {e}") from e


def process_trial(nct_id: str, verbose: bool = False) -> IdentifiedTrial:
    """
    Processes a trial by fetching data and structurizing criteria.

    Args:
        nct_id (str): The NCT ID of the clinical trial.
        verbose (bool): Whether to print detailed output.

    Returns:
        Optional[Trial]: The processed trial or None if failed.
    """
    raw_data = get_trial_data(nct_id)
    if not raw_data:
        raise ValueError(f"Failed to fetch trial data for NCT ID: {nct_id}")
    processedTrial: IdentifiedTrial = identify_line_by_line(raw_data)
    
    logger.info("Trial processing complete for NCT ID: %s", nct_id)
    logger.info("Processed trial: %s", processedTrial)
    
    return processedTrial
