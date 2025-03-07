# services/structurizer.py

import logging
import re
from typing import List

import rich
from models.identified_criteria import RawTrialData
from models.identified_criteria import LLMSingleRawCriterion, IdentifiedTrial, IdentifiedLine, RawTrialData, LLMIdentifiedLineResponse
from utils.openai_client import get_openai_client
from enum import Enum

logger = logging.getLogger(__name__)

client = get_openai_client()


def identify_criterions_from_rawTrial(trial: RawTrialData) -> IdentifiedTrial:
    """
    Structurizes the trial's eligibility criteria using a bottom-up approach.

    Args:
        trial (Trial): The trial containing raw eligibility criteria.
        verbose (bool): Whether to print detailed output.

    Returns:
        Optional[StructuredCriteria]: The structured criteria or None if failed.
    """
    logger.info("Starting identification of criteria for trial NCT ID: %s", trial.nct_id)
    rich.print(trial)
    
    inclusion_criteria_lines, inclusion_failed = process_lines(trial.inclusion_criteria)
    exclusion_criteria_lines, exclusion_failed = process_lines(trial.exclusion_criteria)
    miscellaneous_criteria_lines, miscellaneous_failed = process_lines(trial.miscellaneous_criteria)

    # Combine the results into the IdentifiedTrial object
    identified_trial = IdentifiedTrial(
        info=trial,
        inclusion_lines=inclusion_criteria_lines,
        exclusion_lines=exclusion_criteria_lines,
        miscellaneous_lines=miscellaneous_criteria_lines,
        failed_inclusion=inclusion_failed,
        failed_exclusion=exclusion_failed,
        failed_miscellaneous=miscellaneous_failed
    )
    

    if inclusion_criteria_lines or exclusion_criteria_lines or miscellaneous_criteria_lines:
        logger.info("Successfully structurized trial NCT ID: %s", trial.nct_id)
        return identified_trial
    else:
        logger.warning("No atomic criteria extracted for trial NCT ID: %s", trial.nct_id)
        raise ValueError(f"No atomic criteria extracted for trial NCT ID: {trial.nct_id}\nThis was the failed result: {identified_trial}")

def process_lines(section_text : str) -> tuple[list[IdentifiedLine], list[IdentifiedLine]]:
    lines = [line.strip() for line in re.split(r'[\n\r]+', section_text) if line.strip()]
    identified_criteria_lines:List[IdentifiedLine] = []
    failed: List[IdentifiedLine] = []

    for index, line in enumerate(lines):
        logger.debug("Processing line %d: %s", index + 1, line)
        if extracted_criteria := extract_atomic_criteria_from_line(line).atomic_criteria:
            try:
                # Verify criteria and identify leftovers
                verify(line, extracted_criteria)
                identified_criteria_lines.append(IdentifiedLine(line=line, criterions=extracted_criteria))
            except ValueError as e:
                logger.error("Error validating line %d: %s", index + 1, e)
                failed.append(IdentifiedLine(line=line, criterions=extracted_criteria))
                continue
        else:
            logger.warning("Failed to extract criteria from line %d.", index + 1)
            failed.append(IdentifiedLine(line=line, criterions=[]))
    return identified_criteria_lines, failed

def extract_atomic_criteria_from_line(line: str) -> LLMIdentifiedLineResponse:
    """
    Sends a line to the LLM to extract atomic criteria.

    Args:
        line (str): The line of text to process.

    Returns:
        Optional[List[AtomicCriterion]]: A list of AtomicCriterion objects.
    """
    logger.debug("Extracting atomic criteria from line: %s", line)
    prompt = (
        "You are an expert in clinical trial eligibility criteria."
        "Given the following line from an Oncological Clinical Trial Eligibility Criteria, extract every individual criterion they are testing the patient for."
        "In other words, what are the specific properties/attributes/conditions that are being tested for in the patient?"
        "For each criterion, provide the exact snippets from the line that you used to identify it."
        "Should your exact snippets be non-contiguous then provide multiple short exact snippets"
    )
    

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": line},
            ],
            temperature=0.0,
            response_format=LLMIdentifiedLineResponse,
        )
        if response := completion.choices[0].message.parsed:
            logger.debug("Successfully extracted atomic criteria from line: %s", line)
            return response
        else:
            logger.warning("Failed to parse LLM response.")
            raise ValueError(f"Failed to parse LLM response for line: '{line}'")
    except Exception as e:
        logger.error("Error during LLM extraction: %s", e)
        raise ValueError(f"Error during LLM extraction: {e}") from e

def verify(line: str, criteria_list: List[LLMSingleRawCriterion]) -> None:
    """
    Verifies that each criterion's raw_text is an exact substring of the line and extracts leftovers.

    Args:
        line (str): The original line of text.
        criteria_list (List[AtomicCriterion]): List of extracted criteria.

    Returns:
        List[str]: List of leftover text segments between the criteria.

    Raises:
        ValueError: If any criterion's raw_text is not found in the line.
    """
    logger.info("Verifying criteria and extracting leftovers.")

    for criterion in criteria_list:
        for snippet in criterion.exact_snippets:
            # Find the raw_text in line starting from index i
            index = line.replace("\\", "").find(snippet.replace("\\", ""))
            if index == -1:
                logger.error("Criterion snippet not found in line. Line: '%s', Raw text: '%s'", line, snippet)
                raise ValueError(f"Criterion raw_text not found in line. Line: '{line}', Raw text: '{snippet}'")

