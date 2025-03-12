# models/logical_criteria.py
"""
Data Models for Logical Structured Clinical Trial Criteria

This module defines the Pydantic models used to represent the logical relationships
between atomic criteria extracted from clinical trial eligibility criteria.

Classes prefixed with 'LLM' are used as output formats for LLM processing, while
other classes are used for internal data storage.

Classes:
    LLMLogicalAnd: Logical AND relationship between criteria.
    LLMLogicalOr: Logical OR relationship between criteria.
    LLMLogicalNot: Logical NOT operation on criteria.
    LLMLogicalXor: Logical XOR relationship between criteria.
    LLMLogicalConditional: Conditional (if-then-else) relationship.
    LLMLogicalWrapperResponse: Container for LLM logical structure response.
    LogicalLine: Line with identified criteria and logical structure.
    LogicalTrial: Complete trial with logically structured criteria.

Important:
    The docstrings of Pydantic models are used as prompts for LLM processing.
    Changing these docstrings will alter how the LLM interprets the output format.
    Use code comments rather than docstring modifications if documentation changes
    are needed without affecting LLM behavior.
"""

from typing import List, Union

from pydantic import BaseModel, Field

from src.models.identified_criteria import (
    RawTrialData,
    Requirement,
)


class SingleRequirementCriterion(BaseModel):
    """
    Represents an atomic criterion with a single requirement extracted from the eligibility criteria.

    example:
        input:
        "Tissue from tumor must be available and > 2 cm in diameter.",

        output:
        "exact_snippets": "Tissue from tumor must be available ... > 2 cm in diameter.",
        "criterion": "tumor tissue",
        "requirement": {
            "requirement_type": "availability",
            "expected_value": true
        }
    """

    exact_snippets: str = Field(
        ...,
        description="Exact text snippets from the eligibility criteria that were used to extract this criterion, using ellipses (...) for non-consecutive text.",
    )

    criterion: str = Field(
        ...,
        description="The specific property, attribute, or condition that is being tested (e.g., 'age', 'lung cancer', 'BMI').",
    )

    requirement: Requirement = Field(
        ..., description="The requirement and its expected value for the criterion."
    )

    # needed to make this hashable for validating logical structures
    def __eq__(self, other):
        if isinstance(other, SingleRequirementCriterion):
            return str(self) == str(other)
        return False

    def __hash__(self):
        return hash((tuple(self.exact_snippets), self.criterion, self.requirement))


class IdentifiedUnrolledLine(BaseModel):
    """
    Represents a structured line of eligibility criteria.
    """

    line: str = Field(..., description="The original line of eligibility criteria.")
    criterions: List[SingleRequirementCriterion] = Field(
        ..., description="List of structured criteria."
    )


class LLMLogicalAnd(BaseModel):
    """
    Represents a logical AND relationship between criteria.
    """

    and_criteria: List[
        Union[
            SingleRequirementCriterion,
            "LLMLogicalAnd",
            "LLMLogicalOr",
            "LLMLogicalNot",
            "LLMLogicalXor",
            "LLMLogicalConditional",
        ]
    ] = Field(..., description="The criteria involved in the relationship.")


class LLMLogicalOr(BaseModel):
    """
    Represents a logical OR relationship between criteria.
    """

    or_criteria: List[
        Union[
            SingleRequirementCriterion,
            "LLMLogicalAnd",
            "LLMLogicalOr",
            "LLMLogicalNot",
            "LLMLogicalXor",
            "LLMLogicalConditional",
        ]
    ] = Field(..., description="The criteria involved in the relationship.")


class LLMLogicalNot(BaseModel):
    """
    Represents a logical NOT operation on a criterion or logical expression. Ensure that negation isn't already implicit in the criterion's value (e.g., 'must not be older than 18' is already represented by 'age ≤ 18 and no need for additional LLMLogicalNot').
    """

    not_criteria: Union[
        SingleRequirementCriterion,
        "LLMLogicalAnd",
        "LLMLogicalOr",
        "LLMLogicalNot",
        "LLMLogicalXor",
        "LLMLogicalConditional",
    ] = Field(..., description="The criteria involved in the relationship.")


class LLMLogicalXor(BaseModel):
    """
    Represents a logical XOR relationship between criteria.
    """

    xor_criteria: List[
        Union[
            SingleRequirementCriterion,
            "LLMLogicalAnd",
            "LLMLogicalOr",
            "LLMLogicalNot",
            "LLMLogicalXor",
            "LLMLogicalConditional",
        ]
    ] = Field(..., description="The criteria involved in the relationship.")


class LLMLogicalConditional(BaseModel):
    """
    Represents a conditional relationship between criteria.
    """

    condition: Union[
        SingleRequirementCriterion,
        "LLMLogicalAnd",
        "LLMLogicalOr",
        "LLMLogicalNot",
        "LLMLogicalXor",
        "LLMLogicalConditional",
    ] = Field(..., description="The condition criterion (antecedent)")
    then_criteria: Union[
        SingleRequirementCriterion,
        "LLMLogicalAnd",
        "LLMLogicalOr",
        "LLMLogicalNot",
        "LLMLogicalXor",
        "LLMLogicalConditional",
        None,
    ] = Field(
        ...,
        description="The criteria that apply if the condition (antecedent) is met. (consequent)",
    )
    else_criteria: Union[
        SingleRequirementCriterion,
        "LLMLogicalAnd",
        "LLMLogicalOr",
        "LLMLogicalNot",
        "LLMLogicalXor",
        "LLMLogicalConditional",
        None,
    ] = Field(
        ...,
        description="The criteria that apply if the condition (antecedent) is not met (optional consequent).",
    )


# Rebuild model schemas to resolve forward references in the Union types
LLMLogicalAnd.model_rebuild()
LLMLogicalOr.model_rebuild()
LLMLogicalNot.model_rebuild()
LLMLogicalXor.model_rebuild()
LLMLogicalConditional.model_rebuild()


# This wrapper is necessary because the LLM needs a single type to generate,
# not a Union of possible logical relation types
class LLMLogicalWrapperResponse(BaseModel):
    """
    Represents the response from the LLM.
    """

    logicalRepresentation: Union[
        LLMLogicalAnd, LLMLogicalOr, LLMLogicalNot, LLMLogicalXor, LLMLogicalConditional
    ] = Field(..., description="The logical representation of the criteria.")


class LogicalLine(BaseModel):
    """
    Represents a line of eligibility criteria that has been logically structured.
    """

    identified_line: IdentifiedUnrolledLine = Field(
        ..., description="The identified line this was made from."
    )
    logical_structure: Union[
        SingleRequirementCriterion,
        LLMLogicalAnd,
        LLMLogicalOr,
        LLMLogicalNot,
        LLMLogicalXor,
        LLMLogicalConditional,
    ] = Field(..., description="The logically structured Criteria.")
    # Note: We don't use a Pydantic validator here to check if the logical_structure
    # includes all of the identified_line's criteria because we want to be able to
    # store failed lines. This validation happens in the "logify" procedure instead.


class LogicalTrial(BaseModel):
    """
    Represents a complete trial with logically structured eligibility criteria.
    """

    info: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    inclusion_lines: List[LogicalLine] = Field(
        ..., description="List of inclusion lines successfully logically structurized."
    )
    exclusion_lines: List[LogicalLine] = Field(
        ..., description="List of exclusion lines successfully logically structurized."
    )
    miscellaneous_lines: List[LogicalLine] = Field(
        ...,
        description="List of miscellaneous lines successfully logically structurized.",
    )
    failed_inclusion: List[LogicalLine] = Field(
        ...,
        description="List of inclusion lines that failed to be logically structurized.",
    )
    failed_exclusion: List[LogicalLine] = Field(
        ...,
        description="List of exclusion lines that failed to be logically structurized.",
    )
    failed_miscellaneous: List[LogicalLine] = Field(
        ...,
        description="List of miscellaneous lines that failed to be logically structurized.",
    )
