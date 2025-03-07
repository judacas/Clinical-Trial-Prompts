from enum import Enum
import rich
from models.logical_criteria import LLMLogicalAnd, LLMLogicalNot, LLMLogicalOr, LLMLogicalXor, LLmLogicalConditional, LogicalLine, LogicalTrial, LLMLogicalWrapperResponse
from models.identified_criteria import *
from utils.openai_client import get_openai_client
import logging
from repositories.trial_repository import load_pydantic_from_json

logger = logging.getLogger()

client = get_openai_client()


class CriteriaType(Enum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    MISCELLANEOUS = "miscellaneous"


type_to_note = {
    CriteriaType.INCLUSION: "Note that this is an inclusion criterion, so should this evaluate to true, the patient will qualify for the clinical trial",
    CriteriaType.EXCLUSION: "Note that this is an exclusion criterion, so should this evaluate to true, the patient will not qualify for the clinical trial",
    CriteriaType.MISCELLANEOUS: "Treat the line evaluating to true as qualifying for the clinical trial and false as not qualifying for the clinical trial",
}


def logically_structurize_line(
    line: IdentifiedLine, criteria_type: CriteriaType) -> LogicalLine:
    """
    Structurizes the criteria of a line into logical relationships.
    """

    prompt = (
        "You are an expert in clinical trial eligibility criteria.\n"
        "Given the following line from an Oncological Clinical Trial Eligibility Criteria and its individual criteria, structurize the criteria into logical relationships.\n"
    )

    prompt += type_to_note[criteria_type]

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": str(line)},
            ],
            temperature=0.0,
            response_format=LLMLogicalWrapperResponse,
        )
        response = completion.choices[0].message.parsed
        if response is None:
            logger.warning("Failed to parse LLM response.")
            print(completion.choices[0])
            raise ValueError(f"Failed to parse LLM response for line: '{line}'")
        
    except Exception as e:
        logger.error("Error during LLM extraction: %s", e)
        raise ValueError(f"Error during LLM extraction: {e}") from e
    
    logger.debug("Successfully extracted atomic criteria from line: %s", line)
    logger.debug("LLM response: %s", response)
    
    return LogicalLine(
        identified_line=line, logical_structure=response.logicalRepresentation
    )
    
    
def confirm_criteria_presence(logical_line: LogicalLine):
    """
    Verifies that all SingleRawCriterion instances in the IdentifiedLine are present in the logical structure.

    Args:
        logical_line (LogicalLine): The logical line to verify.
    """
    identified_criteria = {criterion.criterion for criterion in logical_line.identified_line.criterions}
    logical_criteria = extract_criteria_from_logical_structure(logical_line.logical_structure)

    if missing_criteria := identified_criteria - logical_criteria:
        raise ValueError(f"Missing criteria in logical structure: {missing_criteria}")
    else:
        logger.info("All criteria present in logical structure.")

    
def extract_criteria_from_logical_structure(logical_structure) -> set:
    """
    Recursively extracts criteria from the logical structure to make a set of all criteria involved.

    Args:
        logical_structure: The logical structure to extract criteria from.

    Returns:
        set: A set of criteria found in the logical structure.
    """
    criteria = set()

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
    elif isinstance(logical_structure, LLmLogicalConditional):
        criteria.update(extract_criteria_from_logical_structure(logical_structure.condition))
        if logical_structure.then_criteria:
            criteria.update(extract_criteria_from_logical_structure(logical_structure.then_criteria))
        if logical_structure.else_criteria:
            criteria.update(extract_criteria_from_logical_structure(logical_structure.else_criteria))

    return criteria


def logically_structurize_trial(trial: IdentifiedTrial) -> LogicalTrial:
    """
    Structurizes the criteria of a trial into logical relationships.

    Args:
        trial (IdentifiedTrial): The trial to structurize.

    Returns:
        IdentifiedTrial: The trial with logically structured criteria.
    """
    inclusion_lines = []
    exclusion_lines = []
    miscellaneous_lines = []
    failed_inclusion = []
    failed_exclusion = []
    failed_miscellaneous = []

    #NOTE: we treat failed inclusions the same for now as successful inclusions in the identification step
    # NOTE: we treat failed inclusions the same for now as successful inclusions in the identification step
    for inclusion_line in (trial.inclusion_lines + trial.failed_inclusion):
        try:
            logical_line = logically_structurize_line(inclusion_line, CriteriaType.INCLUSION)
            try:
                confirm_criteria_presence(logical_line)
                inclusion_lines.append(logical_line)
            except ValueError as validation_error:
                logger.error("Validation failed for inclusion line: %s", inclusion_line)
                failed_inclusion.append(logical_line)
        except Exception as e:
            logger.error("Failed to structurize inclusion line: %s", inclusion_line)
            failed_inclusion.append(LogicalLine(identified_line=inclusion_line, logical_structure=LLMSingleRawCriterion(criterion="failed", requirement_type="failed", expected_value="failed", exact_snippets=["failed"])))

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
            failed_exclusion.append(LogicalLine(identified_line=exclusion_line, logical_structure=LLMSingleRawCriterion(criterion="failed", requirement_type="failed", expected_value="failed", exact_snippets=["failed"])))

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
            failed_miscellaneous.append(LogicalLine(identified_line=miscellaneous_line, logical_structure=LLMSingleRawCriterion(criterion="failed", requirement_type="failed", expected_value="failed", exact_snippets=["failed"])))


    return LogicalTrial(
        info=trial.info,
        inclusion_lines=inclusion_lines,
        exclusion_lines=exclusion_lines,
        miscellaneous_lines=miscellaneous_lines,
        failed_inclusion=failed_inclusion,
        failed_exclusion=failed_exclusion,
        failed_miscellaneous=failed_miscellaneous
    )