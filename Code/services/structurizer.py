# services/structurizer.py

import logging
import re
from typing import List, Optional
from models.LLM_responses import oneParsedLine
from models.structured_criteria import RawTrialData
from models.structured_criteria import SingleRawCriterion, ParsedTrial, structuredLine
from utils.openai_client import get_openai_client
import rich

logger = logging.getLogger(__name__)

client = get_openai_client()

def structurize_bottom_up(trial: RawTrialData) -> ParsedTrial:
    """
    Structurizes the trial's eligibility criteria using a bottom-up approach.

    Args:
        trial (Trial): The trial containing raw eligibility criteria.
        verbose (bool): Whether to print detailed output.

    Returns:
        Optional[StructuredCriteria]: The structured criteria or None if failed.
    """
    logger.info("Starting bottom-up structurization for trial NCT ID: %s", trial.nct_id)

    raw_text = trial.criteria
    print(trial)
    lines = [line.strip() for line in re.split(r'[\n\r]+', raw_text) if line.strip()]
    logger.debug("Split raw text into %d lines.", len(lines))

    structured_lines:List[structuredLine] = []
    failed: List[structuredLine] = []

    for index, line in enumerate(lines):
        logger.debug("Processing line %d: %s", index + 1, line)
        if extracted_criteria := extract_atomic_criteria_from_line(line).atomic_criteria:
            try:
                # Verify criteria and identify leftovers
                verify(line, extracted_criteria)
                structured_lines.append(structuredLine(line=line, criterions=extracted_criteria))
            except ValueError as e:
                logger.error("Error processing line %d: %s", index + 1, e)
                failed.append(structuredLine(line=line, criterions=extracted_criteria))
                continue
        else:
            logger.warning("Failed to extract criteria from line %d.", index + 1)
            failed.append(structuredLine(line=line, criterions=[]))

    if structured_lines:
        structured_criteria = ParsedTrial(info=trial, lines=structured_lines, failed=failed)
        logger.info("Successfully structurized trial NCT ID: %s", trial.nct_id)
        return structured_criteria
    else:
        logger.warning("No atomic criteria extracted for trial NCT ID: %s", trial.nct_id)
        raise ValueError(f"No atomic criteria extracted for trial NCT ID: {trial.nct_id}")



def extract_atomic_criteria_from_line(line: str) -> oneParsedLine:
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
        "For each criterion, provide the exact quotes from the line that you used to identify it."
        "Should your exact text be non-contiguous then provide multiple exact snippets"
        
    )

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": line},
            ],
            temperature=0.0,
            response_format=oneParsedLine,
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

def verify(line: str, criteria_list: List[SingleRawCriterion]) -> None:
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

