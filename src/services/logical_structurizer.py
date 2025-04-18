# services/logical_structurizer.py
"""
Clinical Trial Logical Structurizing Service

This module is responsible for organizing identified criteria from clinical trial eligibility
text into logical structures. It uses LLM-based processing to determine the relationships
between atomic criteria (AND, OR, NOT, XOR, conditional statements).

The structurizing process follows these steps:
1. Process each line in the identified trial data
2. Transform atomic criteria into logical structures using an LLM
3. Verify that all identified criteria are present in the logical structure
4. Organize results into comprehensive logical models

Functions:
    logically_structurize_line: Transform an identified line into a logical structure.
    confirm_criteria_presence: Verify completeness of logical structure against identified criteria.
    extract_criteria_from_logical_structure: Recursively extract all criteria from a logical structure.
    logically_structurize_trial: Process an entire trial's criteria into logical structures.
"""

import logging
from enum import Enum
from typing import List, Union

from src.models.identified_criteria import IdentifiedLine, IdentifiedTrial, Requirement
from src.models.logical_criteria import (
    IdentifiedUnrolledLine,
    LLMLogicalAnd,
    LLMLogicalConditional,
    LLMLogicalNot,
    LLMLogicalOr,
    LLMLogicalWrapperResponse,
    LLMLogicalXor,
    LogicalLine,
    LogicalTrial,
    SingleRequirementCriterion,
)
from src.utils.config import TEMPERATURE, TIMEOUT
from src.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = get_openai_client()


class CriteriaType(Enum):
    """Enum for different types of clinical trial criteria."""

    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    MISCELLANEOUS = "miscellaneous"


# Mapping of criteria types to explanatory notes for the LLM
type_to_note = {
    CriteriaType.INCLUSION: "Note that this is an inclusion criterion, so should this evaluate to true, the patient will qualify for the clinical trial",
    CriteriaType.EXCLUSION: "Note that this is an exclusion criterion, so should this evaluate to true, the patient will not qualify for the clinical trial",
    CriteriaType.MISCELLANEOUS: "Treat the line evaluating to true as qualifying for the clinical trial and false as not qualifying for the clinical trial",
}


def UnrollLine(line: IdentifiedLine) -> IdentifiedUnrolledLine:
    """
    Split each LLMMultiRequirementCriterion with multiple requirements into multiple criteria, each with one requirement.

    Args:
        line (IdentifiedLine): The line containing identified atomic criteria.

    Returns:
        IdentifiedUnrolledLine: The line with criteria, each with a single requirement.
    """
    split_criteria: list[SingleRequirementCriterion] = []
    for criterion in line.criterions:
        split_criteria.extend(
            SingleRequirementCriterion(
                exact_snippets=criterion.exact_snippets,
                criterion=criterion.criterion,
                requirement=requirement,
            )
            for requirement in criterion.requirements
        )
    return IdentifiedUnrolledLine(line=line.line, criterions=split_criteria)


def logically_structurize_line(
    line: IdentifiedUnrolledLine, criteria_type: CriteriaType
) -> LogicalLine:
    """
    Transform an identified line's criteria into logical relationships.

    Args:
        line (IdentifiedUnrolledLine): The line containing identified atomic criteria.
        criteria_type (CriteriaType): The type of criteria (inclusion, exclusion, miscellaneous).

    Returns:
        LogicalLine: The line with structured logical relationships between criteria.

    Raises:
        ValueError: If the LLM structurizing process fails.
    """
    logger.debug("Structurizing line: %s", line)

    # Define the system prompt for the LLM
    prompt = (
        "You are an expert in clinical trial eligibility criteria.\n"
        "Given the following line from an Oncological Clinical Trial Eligibility Criteria and its individual atomic criteria, structurize the criteria into logical relationships.\n"
        "You may only use the atomic criteria provided, do not add any new criteria. Instead you are to \n"
    )

    # Add context about how this criteria type affects qualification
    prompt += type_to_note[criteria_type]

    try:
        # Send the line to the LLM for logical structurizing
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": str(line)},
            ],
            temperature=TEMPERATURE,
            response_format=LLMLogicalWrapperResponse,
            timeout=TIMEOUT,
        )

        if response := completion.choices[0].message.parsed:
            logger.debug("Successfully structured line logically: %s", line)
            logger.debug("LLM response: %s", response)
        else:
            logger.warning("Failed to parse LLM response.\n%s", completion.choices[0])
            raise ValueError(f"Failed to parse LLM response for line: '{line}'")

    except Exception as e:
        logger.error("Error during LLM structurizing: %s", e)
        raise ValueError(f"Error during LLM structurizing: {e}") from e

    return LogicalLine(
        identified_line=line, logical_structure=response.logicalRepresentation
    )


def confirm_criteria_presence(logical_line: LogicalLine) -> None:
    """
    Verifies that all SingleRawCriterion instances in the IdentifiedLine are present in the logical structure.

    Args:
        logical_line (LogicalLine): The logical line to verify.

    Raises:
        ValueError: If any identified criteria are missing from the logical structure.
    """

    logger.info("Verifying criteria presence for line: %s", logical_line)
    # Extract all criteria from the identified line
    identified_criteria: List[SingleRequirementCriterion] = (
        logical_line.identified_line.criterions
    )

    # Extract all criteria from the logical structure
    logical_criteria: list[SingleRequirementCriterion] = (
        extract_criteria_from_logical_structure(logical_line.logical_structure)
    )

    logger.info("Identified criteria: %s", identified_criteria)
    logger.info("Logical criteria: %s", logical_criteria)
    logger.info("Checking for missing criteria...")

    # Check if criteria sets match exactly (no missing, no extras)
    identified_set = set(identified_criteria)
    logical_set = set(logical_criteria)

    if identified_set != logical_set:
        identifyDifference(identified_set, logical_set)
    else:
        logger.info("Criteria sets match exactly - no missing or extra criteria.")


# TODO Rename this here and in `confirm_criteria_presence`
def identifyDifference(identified_set, logical_set):
    missing = identified_set - logical_set
    extra = logical_set - identified_set

    error_msg = ""
    if missing:
        error_msg += f"Missing criteria in logical structure: {missing}. "
    if extra:
        error_msg += f"Extra criteria in logical structure: {extra}. "

    logger.error(error_msg)
    raise ValueError(error_msg)


def extract_criteria_from_logical_structure(
    logical_structure: Union[
        SingleRequirementCriterion,
        LLMLogicalAnd,
        LLMLogicalOr,
        LLMLogicalNot,
        LLMLogicalXor,
        LLMLogicalConditional,
    ],
) -> List[SingleRequirementCriterion]:
    """
    Recursively extracts criteria from the logical structure to make a set of all criteria involved.

    Args:
        logical_structure: The logical structure to extract criteria from (can be any logical type).

    Returns:
        set: A set of criteria found in the logical structure.
    """
    criteria: list[SingleRequirementCriterion] = []

    # Handle different types of logical structures recursively
    if isinstance(logical_structure, SingleRequirementCriterion):
        criteria.append(logical_structure)
    elif isinstance(logical_structure, LLMLogicalAnd):
        for sub_criteria in logical_structure.and_criteria:
            criteria.extend(extract_criteria_from_logical_structure(sub_criteria))
    elif isinstance(logical_structure, LLMLogicalOr):
        for sub_criteria in logical_structure.or_criteria:
            criteria.extend(extract_criteria_from_logical_structure(sub_criteria))
    elif isinstance(logical_structure, LLMLogicalNot):

        criteria.extend(
            extract_criteria_from_logical_structure(logical_structure.not_criteria)
        )
    elif isinstance(logical_structure, LLMLogicalXor):
        for sub_criteria in logical_structure.xor_criteria:
            criteria.extend(extract_criteria_from_logical_structure(sub_criteria))
    elif isinstance(logical_structure, LLMLogicalConditional):
        criteria.extend(
            extract_criteria_from_logical_structure(logical_structure.condition)
        )
        if logical_structure.then_criteria:
            criteria.extend(
                extract_criteria_from_logical_structure(logical_structure.then_criteria)
            )
        if logical_structure.else_criteria:
            criteria.extend(
                extract_criteria_from_logical_structure(logical_structure.else_criteria)
            )

    return criteria


def process_criteria_lines(
    lines: list[IdentifiedLine], criteria_type: CriteriaType
) -> tuple[list[LogicalLine], list[LogicalLine]]:
    """
    Process a list of criteria lines into logical structures.

    Args:
        lines (list[IdentifiedLine]): The list of identified lines to process.
        criteria_type (CriteriaType): The type of criteria (inclusion, exclusion, miscellaneous).

    Returns:
        tuple: A tuple containing:
            - List of successfully structured logical lines
            - List of lines that failed to be structured
    """
    successful_lines = []
    failed_lines = []

    for line in lines:
        unrolled_line = UnrollLine(line)
        try:
            # Attempt to structurize the line
            logical_line = logically_structurize_line(unrolled_line, criteria_type)
            try:
                # Verify criteria completeness
                confirm_criteria_presence(logical_line)
                successful_lines.append(logical_line)
            except ValueError as validation_error:
                logger.error(
                    "Validation failed for %s line: %s", criteria_type.value, line
                )
                logger.error("Validation error: %s", validation_error)
                failed_lines.append(logical_line)
        except Exception as e:
            logger.error("Failed to structurize %s line: %s", criteria_type.value, line)
            logger.error("Error: %s", e)
            # Create a placeholder for failed lines
            failed_lines.append(
                LogicalLine(
                    identified_line=unrolled_line,
                    logical_structure=SingleRequirementCriterion(
                        exact_snippets="failed",
                        criterion="failed",
                        requirement=Requirement(
                            requirement_type="failed", expected_value="failed"
                        ),
                    ),
                )
            )

    return successful_lines, failed_lines


def logically_structurize_trial(trial: IdentifiedTrial) -> LogicalTrial:
    """
    Structurizes all criteria lines of a trial into logical relationships.

    Args:
        trial (IdentifiedTrial): The identified trial to be structurized.

    Returns:
        LogicalTrial: The trial with logically structured criteria.
    """
    logger.info(
        "Starting logical structurizing for trial NCT ID: %s", trial.info.nct_id
    )

    # Process inclusion criteria
    logger.debug(
        "Processing %d inclusion criteria lines",
        len(trial.inclusion_lines) + len(trial.failed_inclusion),
    )
    inclusion_lines, failed_inclusion = process_criteria_lines(
        trial.inclusion_lines + trial.failed_inclusion, CriteriaType.INCLUSION
    )

    # Process exclusion criteria
    logger.debug(
        "Processing %d exclusion criteria lines",
        len(trial.exclusion_lines) + len(trial.failed_exclusion),
    )
    exclusion_lines, failed_exclusion = process_criteria_lines(
        trial.exclusion_lines + trial.failed_exclusion, CriteriaType.EXCLUSION
    )

    # Process miscellaneous criteria
    logger.debug(
        "Processing %d miscellaneous criteria lines",
        len(trial.miscellaneous_lines) + len(trial.failed_miscellaneous),
    )
    miscellaneous_lines, failed_miscellaneous = process_criteria_lines(
        trial.miscellaneous_lines + trial.failed_miscellaneous,
        CriteriaType.MISCELLANEOUS,
    )

    logger.info(
        "Completed logical structurizing for trial NCT ID: %s", trial.info.nct_id
    )
    return LogicalTrial(
        info=trial.info,
        inclusion_lines=inclusion_lines,
        exclusion_lines=exclusion_lines,
        miscellaneous_lines=miscellaneous_lines,
        failed_inclusion=failed_inclusion,
        failed_exclusion=failed_exclusion,
        failed_miscellaneous=failed_miscellaneous,
    )
