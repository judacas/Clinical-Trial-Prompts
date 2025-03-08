# services/identifier.py
"""
Clinical Trial Criteria Identification Service

This module is responsible for extracting atomic criteria from clinical trial eligibility
criteria text. It uses LLM-based extraction to identify individual criteria and their
properties from natural language descriptions.

The identification process follows these steps:
1. Split criteria text into lines
2. For each line, extract atomic criteria using an LLM
3. Verify that extracted criteria match the source text
4. Organize results into structured data models

Functions:
    identify_criterions_from_rawTrial: Extract criteria from a raw trial.
    process_lines: Process a section of eligibility criteria into structured lines.
    extract_atomic_criteria_from_line: Extract atomic criteria from a single line.
    verify: Verify that extracted criteria match the source text.
"""

import logging
import re
from typing import List, Tuple

import rich
from src.models.identified_criteria import RawTrialData
from src.models.identified_criteria import LLMSingleRawCriterion, IdentifiedTrial, IdentifiedLine, RawTrialData, LLMIdentifiedLineResponse
from src.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = get_openai_client()


def identify_criterions_from_rawTrial(trial: RawTrialData) -> IdentifiedTrial:
    """
    Extract and structure atomic criteria from a clinical trial's eligibility criteria.
    
    Args:
        trial (RawTrialData): The trial containing raw eligibility criteria.
    
    Returns:
        IdentifiedTrial: The structured criteria extracted from the trial.
        
    Raises:
        ValueError: If no atomic criteria could be extracted from the trial.
    """
    logger.info("Starting identification of criteria for trial NCT ID: %s", trial.nct_id)
    if logger.level <= logging.DEBUG:
        rich.print(trial)  # Using rich.print for better readability in debug mode
    
    # Process each section of criteria
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
    
    # Check if any criteria were successfully extracted
    if inclusion_criteria_lines or exclusion_criteria_lines or miscellaneous_criteria_lines:
        logger.info("Successfully identified criteria for trial NCT ID: %s", trial.nct_id)
        return identified_trial
    else:
        logger.warning("No atomic criteria extracted for trial NCT ID: %s", trial.nct_id)
        raise ValueError(f"No atomic criteria extracted for trial NCT ID: {trial.nct_id}\nThis was the failed result: {identified_trial}")


def process_lines(section_text: str) -> Tuple[List[IdentifiedLine], List[IdentifiedLine]]:
    """
    Process a section of eligibility criteria text into structured lines.
    
    Args:
        section_text (str): The text of a criteria section (inclusion, exclusion, or miscellaneous).
        
    Returns:
        tuple: A tuple containing:
            - List of successfully identified lines with structured criteria
            - List of lines that failed to be processed correctly
    """
    # Split the text into individual lines
    lines = [line.strip() for line in re.split(r'[\n\r]+', section_text) if line.strip()]
    identified_criteria_lines: List[IdentifiedLine] = []
    failed: List[IdentifiedLine] = []

    for index, line in enumerate(lines):
        logger.debug("Processing line %d: %s", index + 1, line)
        
        # Extract atomic criteria from the line
        extracted_response = extract_atomic_criteria_from_line(line)
        extracted_criteria = extracted_response.atomic_criteria
        
        if extracted_criteria:
            try:
                # Verify that criteria match the source text
                verify(line, extracted_criteria)
                identified_criteria_lines.append(IdentifiedLine(line=line, criterions=extracted_criteria))
            except ValueError as e:
                logger.error("Error validating line %d: %s", index + 1, e)
                failed.append(IdentifiedLine(line=line, criterions=extracted_criteria))
        else:
            logger.warning("Failed to extract criteria from line %d.", index + 1)
            failed.append(IdentifiedLine(line=line, criterions=[]))
            
    return identified_criteria_lines, failed


def extract_atomic_criteria_from_line(line: str) -> LLMIdentifiedLineResponse:
    """
    Extract atomic criteria from a single line of eligibility criteria text using an LLM.
    
    Args:
        line (str): A single line of eligibility criteria text.
        
    Returns:
        LLMIdentifiedLineResponse: The structured criteria extracted from the line.
        
    Raises:
        ValueError: If the LLM extraction process fails.
    """
    logger.debug("Extracting atomic criteria from line: %s", line)
    
    # Define the system prompt for the LLM
    prompt = (
        "You are an expert in clinical trial eligibility criteria."
        "Given the following line from an Oncological Clinical Trial Eligibility Criteria, extract every individual criterion they are testing the patient for."
        "In other words, what are the specific properties/attributes/conditions that are being tested for in the patient?"
        "For each criterion, provide the exact snippets from the line that you used to identify it."
        "Should your exact snippets be non-contiguous then provide multiple short exact snippets"
    )
    
    try:
        # Send the line to the LLM for processing
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
    Verify that each criterion's exact snippets are found in the line.
    
    Args:
        line (str): The original line of eligibility criteria text.
        criteria_list (List[LLMSingleRawCriterion]): List of extracted criteria.
        
    Raises:
        ValueError: If any criterion's snippet is not found in the line.
    """
    logger.info("Verifying criteria snippets.")

    for criterion in criteria_list:
        for snippet in criterion.exact_snippets:
            # Find the snippet in the line (removing backslashes for comparison)
            index = line.replace("\\", "").find(snippet.replace("\\", ""))
            if index == -1:
                logger.error("Criterion snippet not found in line. Line: '%s', Raw text: '%s'", line, snippet)
                raise ValueError(f"Criterion raw_text not found in line. Line: '{line}', Raw text: '{snippet}'")