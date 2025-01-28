# services/trial_manager.py

import logging
from typing import Optional
from models.structured_criteria import ParsedTrial
from services.structurizer import structurize_bottom_up
from models.structured_criteria import RawTrialData
from models.criterion import Criterion
from utils.helpers import curl_with_status_check
import json
import os

# Configure logging
logger = logging.getLogger(__name__)


def get_trial_data(nct_id: str) -> RawTrialData:
    #! MUST CLEAN UP AND PREPROCESS A BIT MORE. REMOVE THOSE ANNOYING \ THAT ARE MESSING UP STRING COMPARISONS SUCH AS \> OR \<
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
        eligibility = study.get(
            "eligibilityModule", {}
        ).get("eligibilityCriteria", "")       
        
        raw_data = RawTrialData(
            nct_id=nct_id, official_title=official_title, criteria=eligibility
        )
        logger.info("Successfully retrieved trial data.")
        logger.debug("Fully raw input: %s", data)
        logger.debug("Trial data: %s", raw_data)
        return raw_data
    except Exception as e:
        logger.error("Error fetching trial data: %s", e)
        raise ValueError(f"Error fetching trial data: {e}")


def process_trial(nct_id: str, verbose: bool = False) -> ParsedTrial:
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
    processedTrial: ParsedTrial = structurize_bottom_up(raw_data)
    
    logger.info("Trial processing complete for NCT ID: %s", nct_id)
    logger.info("Processed trial: %s", processedTrial)
    
    # Write the Pydantic object out as a JSON file
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{nct_id}_new.json")
    
    with open(output_path, "w") as f:
        json.dump(processedTrial.model_dump_json(), f, indent=4)
    
    return processedTrial
