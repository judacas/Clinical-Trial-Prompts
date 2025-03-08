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

from enum import Enum
import logging
from src.models.logical_criteria import (
    LLMLogicalAnd, 
    LLMLogicalNot, 
    LLMLogicalOr, 
    LLMLogicalXor, 
    LLMLogicalConditional, 
    LogicalLine, 
    LogicalTrial, 
    LLMLogicalWrapperResponse
)
from src.models.identified_criteria import IdentifiedLine, IdentifiedTrial, LLMSingleRawCriterion
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


def logically_structurize_line(
    line: IdentifiedLine, criteria_type: CriteriaType) -> LogicalLine:
    """
    Transform an identified line's criteria into logical relationships.
    
    Args:
        line (IdentifiedLine): The line containing identified atomic criteria.
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
        "Given the following line from an Oncological Clinical Trial Eligibility Criteria and its individual criteria, structurize the criteria into logical relationships.\n"
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
            temperature=0.0,
            response_format=LLMLogicalWrapperResponse,
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
    # Extract all criteria from the identified line
    identified_criteria = {criterion.criterion for criterion in logical_line.identified_line.criterions}
    
    # Extract all criteria from the logical structure
    logical_criteria = extract_criteria_from_logical_structure(logical_line.logical_structure)

    # Check if any criteria are missing
    if missing_criteria := identified_criteria - logical_criteria:
        logger.error("Missing criteria in logical structure: %s", missing_criteria)
        raise ValueError(f"Missing criteria in logical structure: {missing_criteria}")
    else:
        logger.info("All criteria present in logical structure.")

    
def extract_criteria_from_logical_structure(logical_structure) -> set:
    """
    Recursively extracts criteria from the logical structure to make a set of all criteria involved.

    Args:
        logical_structure: The logical structure to extract criteria from (can be any logical type).

    Returns:
        set: A set of criteria found in the logical structure.
    """
    criteria = set()

    # Handle different types of logical structures recursively
    if isinstance(logical_structure, LLMSingleRawCriterion):
        criteria.add(logical_structure.criterion)
    elif isinstance(logical_structure, LLMLogicalAnd):
        for sub_criteria in logical_structure.and_criteria:
            criteria.update(extract_criteria_from_logical_structure(sub_criteria))
    elif isinstance(logical_structure, LLMLogicalOr):
        for sub_criteria in logical_structure.or_criteria:
            criteria.update(extract_criteria_from_logical_structure(sub_criteria))
    elif isinstance(logical_structure, LLMLogicalNot):
        criteria.update(extract_criteria_from_logical_structure(logical_structure.not_criteria))
    elif isinstance(logical_structure, LLMLogicalXor):
        for sub_criteria in logical_structure.xor_criteria:
            criteria.update(extract_criteria_from_logical_structure(sub_criteria))
    elif isinstance(logical_structure, LLMLogicalConditional):
        criteria.update(extract_criteria_from_logical_structure(logical_structure.condition))
        if logical_structure.then_criteria:
            criteria.update(extract_criteria_from_logical_structure(logical_structure.then_criteria))
        if logical_structure.else_criteria:
            criteria.update(extract_criteria_from_logical_structure(logical_structure.else_criteria))

    return criteria


def logically_structurize_trial(trial: IdentifiedTrial) -> LogicalTrial:
    """
    Structurizes all criteria lines of a trial into logical relationships.

    Args:
        trial (IdentifiedTrial): The identified trial to be structurized.

    Returns:
        LogicalTrial: The trial with logically structured criteria.
    """
    logger.info("Starting logical structurizing for trial NCT ID: %s", trial.info.nct_id)
    
    # Initialize result containers
    inclusion_lines = []
    exclusion_lines = []
    miscellaneous_lines = []
    failed_inclusion = []
    failed_exclusion = []
    failed_miscellaneous = []

    # Process inclusion criteria (both successful and failed identifications)
    logger.debug("Processing %d inclusion criteria lines", len(trial.inclusion_lines) + len(trial.failed_inclusion))
    for inclusion_line in (trial.inclusion_lines + trial.failed_inclusion):
        try:
            # Attempt to structurize the line
            logical_line = logically_structurize_line(inclusion_line, CriteriaType.INCLUSION)
            try:
                # Verify criteria completeness
                confirm_criteria_presence(logical_line)
                inclusion_lines.append(logical_line)
            except ValueError as validation_error:
                logger.error("Validation failed for inclusion line: %s", inclusion_line)
                failed_inclusion.append(logical_line)
        except Exception as e:
            logger.error("Failed to structurize inclusion line: %s", inclusion_line)
            # Create a placeholder for failed lines
            failed_inclusion.append(LogicalLine(
                identified_line=inclusion_line, 
                logical_structure=LLMSingleRawCriterion(
                    criterion="failed", 
                    requirement_type="failed", 
                    expected_value="failed", 
                    exact_snippets=["failed"]
                )
            ))

    # Process exclusion criteria
    logger.debug("Processing %d exclusion criteria lines", len(trial.exclusion_lines) + len(trial.failed_exclusion))
    for exclusion_line in (trial.exclusion_lines + trial.failed_exclusion):
        try:
            logical_line = logically_structurize_line(exclusion_line, CriteriaType.EXCLUSION)
            try:
                confirm_criteria_presence(logical_line)
                exclusion_lines.append(logical_line)
            except ValueError as validation_error:
                logger.error("Validation failed for exclusion line: %s", exclusion_line)
                failed_exclusion.append(logical_line)
        except Exception as e:
            logger.error("Failed to structurize exclusion line: %s", exclusion_line)
            failed_exclusion.append(LogicalLine(
                identified_line=exclusion_line, 
                logical_structure=LLMSingleRawCriterion(
                    criterion="failed", 
                    requirement_type="failed", 
                    expected_value="failed", 
                    exact_snippets=["failed"]
                )
            ))

    # Process miscellaneous criteria
    logger.debug("Processing %d miscellaneous criteria lines", len(trial.miscellaneous_lines) + len(trial.failed_miscellaneous))
    for miscellaneous_line in (trial.miscellaneous_lines + trial.failed_miscellaneous):
        try:
            logical_line = logically_structurize_line(miscellaneous_line, CriteriaType.MISCELLANEOUS)
            try:
                confirm_criteria_presence(logical_line)
                miscellaneous_lines.append(logical_line)
            except ValueError as validation_error:
                logger.error("Validation failed for miscellaneous line: %s", miscellaneous_line)
                failed_miscellaneous.append(logical_line)
        except Exception as e:
            logger.error("Failed to structurize miscellaneous line: %s", miscellaneous_line)
            failed_miscellaneous.append(LogicalLine(
                identified_line=miscellaneous_line, 
                logical_structure=LLMSingleRawCriterion(
                    criterion="failed", 
                    requirement_type="failed", 
                    expected_value="failed", 
                    exact_snippets=["failed"]
                )
            ))

    logger.info("Completed logical structurizing for trial NCT ID: %s", trial.info.nct_id)
    return LogicalTrial(
        info=trial.info,
        inclusion_lines=inclusion_lines,
        exclusion_lines=exclusion_lines,
        miscellaneous_lines=miscellaneous_lines,
        failed_inclusion=failed_inclusion,
        failed_exclusion=failed_exclusion,
        failed_miscellaneous=failed_miscellaneous
    )