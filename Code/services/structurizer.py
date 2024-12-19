# services/structurizer.py

import logging
import re
from typing import List, Optional
from models.LLM_responses import oneParsedLine
from models.structured_criteria import RawTrialData
from models.structured_criteria import SingleRawCriterion, ParsedTrial
from utils.openai_client import get_openai_client
import rich

logger = logging.getLogger(__name__)

client = get_openai_client()

def structurize_bottom_up(trial: RawTrialData, verbose: bool = False) -> ParsedTrial:
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

    atomic_criteria_list: List[SingleRawCriterion] = []
    all_leftovers: List[str] = []

    for index, line in enumerate(lines):
        logger.info("Processing line %d: %s", index + 1, line)
        if extracted_criteria := extract_atomic_criteria_from_line(
            line, verbose
        ).atomic_criteria:
            try:
                # Verify criteria and identify leftovers
                leftovers = verify_and_extract_leftovers(line, extracted_criteria)
                atomic_criteria_list.extend(extracted_criteria)
                all_leftovers.extend(leftovers)
            except ValueError as e:
                logger.error("Error processing line %d: %s", index + 1, e)
                continue
        else:
            logger.warning("Failed to extract criteria from line %d.", index + 1)
            all_leftovers.append(line)  # Consider the entire line as leftover

    if atomic_criteria_list:
        structured_criteria = ParsedTrial(
            atomic_criteria=atomic_criteria_list,
            leftovers=all_leftovers,
            info=trial
        )
        logger.info("Successfully structurized trial NCT ID: %s", trial.nct_id)
        return structured_criteria
    else:
        logger.warning("No atomic criteria extracted for trial NCT ID: %s", trial.nct_id)
        raise ValueError(f"No atomic criteria extracted for trial NCT ID: {trial.nct_id}")



def extract_atomic_criteria_from_line(line: str, verbose: bool = False) -> oneParsedLine:
    """
    Sends a line to the LLM to extract atomic criteria.

    Args:
        line (str): The line of text to process.
        verbose (bool): Whether to print detailed output.

    Returns:
        Optional[List[AtomicCriterion]]: A list of AtomicCriterion objects.
    """
    logger.info("Extracting atomic criteria from line.")
    prompt = (
        "You are an expert in clinical trial eligibility criteria. "
        "Given the following line from an Oncological Clinical Trial Eligibility Criteria, extract all possible atomic criteria as specifically as possible. "
        "For each criterion, provide the exact text from the line (must match exactly) and a paraphrased version that makes sense standalone. "
        "An atomic criterion is a single, indivisible criterion that cannot be broken down further."
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
            if verbose:
                rich.print(response)
            logger.info("Successfully extracted atomic criteria from line.")
            return response
        else:
            logger.warning("Failed to parse LLM response.")
            raise ValueError(f"Failed to parse LLM response for line: '{line}'")
    except Exception as e:
        logger.error("Error during LLM extraction: %s", e)
        raise ValueError(f"Error during LLM extraction: {e}")

def verify_and_extract_leftovers(line: str, criteria_list: List[SingleRawCriterion]) -> List[str]:
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
    leftovers = []
    i = 0  # Current index in the line

    for criterion in criteria_list:
        raw_text = criterion.raw_text
        # Find the raw_text in line starting from index i
        index = line.find(raw_text, i)
        if index == -1:
            logger.error("Criterion raw_text not found in line. Line: '%s', Raw text: '%s'", line, raw_text)
            raise ValueError(f"Criterion raw_text not found in line. Line: '{line}', Raw text: '{raw_text}'")
        # Append any text between i and index as leftover
        if index > i:
            leftover_text = line[i:index]
            leftovers.append(leftover_text)
        # Move i to the end of the found raw_text
        i = index + len(raw_text)

    # Append any text remaining after the last criterion as leftover
    if i < len(line):
        leftovers.append(line[i:])

    return leftovers
