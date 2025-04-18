# patient_matching/aggregated_trial_truth.py
"""
This module defines a global aggregated truth table for clinical trial criteria.
Each entry groups a unique (criterion, requirement_type) pair along with a mapping of
trial evaluation groups keyed by the serialized expected value.
Each EvaluationGroup holds:
  - expected_value (the shared expected value)
  - trial_ids: list of trial IDs sharing that expected value
  - truth_value: a shared truth value (initially UNKNOWN)

We use dictionaries for fast lookups internally.
Redundant storage of 'criterion' and 'requirement_type' inside the Pydantic objects is intentional
for self-containment and ease of serialization.
"""

import logging
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field

from src.models.identified_criteria import ExpectedValueType, IdentifiedTrial

logger = logging.getLogger(__name__)


class TruthValue(str, Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


class EvaluationGroup(BaseModel):
    """
    Represents a group of trials sharing the same expected value for a given (criterion, requirement_type) pair.

    Redundancy Note: The expected_value is stored here even though its key is derived from its string form.
    This is intentional for self-containment and ease of serialization.
    """

    expected_value: ExpectedValueType = Field(
        ..., description="The expected value for this group."
    )
    trial_ids: List[str] = Field(
        default_factory=list,
        description="List of trial IDs that share this expected value.",
    )
    truth_value: TruthValue = Field(
        TruthValue.UNKNOWN, description="Shared truth value for this group."
    )


class AggregatedRequirementTruth(BaseModel):
    """
    Represents a requirement type for a given criterion.

    Instead of storing individual trial evaluation entries, we group trials by their expected value.
    Redundancy Note: The 'requirement_type' field is stored here even though it is also used as the key.
    """

    requirement_type: str = Field(
        ..., description="The type of requirement (e.g., 'minimum', 'status')."
    )
    groups: Dict[str, EvaluationGroup] = Field(
        default_factory=dict,
        description="Mapping from serialized expected value to its evaluation group.",
    )


class AggregatedCriterionTruth(BaseModel):
    """
    Represents a criterion with its aggregated requirement entries.

    Redundancy Note: The 'criterion' field is stored here even though it is used as the key in the top-level dict.
    """

    criterion: str = Field(
        ..., description="The criterion name (e.g., 'age', 'lung status')."
    )
    requirements: Dict[str, AggregatedRequirementTruth] = Field(
        default_factory=dict,
        description="Mapping from requirement type to its evaluation.",
    )


class AggregatedTruthTable(BaseModel):
    """
    Represents the complete aggregated truth table across all trials.
    Stores a mapping from normalized criterion to its aggregated truth.
    """

    criteria: Dict[str, AggregatedCriterionTruth] = Field(
        default_factory=dict,
        description="Mapping from criterion to its aggregated truth.",
    )


def aggregate_identified_trials(trials: List[IdentifiedTrial]) -> AggregatedTruthTable:
    """
    Aggregates multiple IdentifiedTrial objects into a single AggregatedTruthTable.

    For each trial, iterates over its atomic criteria (from inclusion, exclusion, and miscellaneous lines).
    Groups them by the normalized criterion name and requirement type, then groups further by the
    expected value (using its string representation as the key).

    Returns:
        AggregatedTruthTable: A global truth table for all trials.
    """
    agg_table = AggregatedTruthTable(criteria={})

    for trial in trials:
        trial_id = trial.info.nct_id
        # Combine all lines from the trial
        all_lines = (
            trial.inclusion_lines + trial.exclusion_lines + trial.miscellaneous_lines
        )
        for line in all_lines:
            for atomic in line.criterions:
                norm_crit = atomic.criterion.strip().lower()
                if norm_crit not in agg_table.criteria:
                    agg_table.criteria[norm_crit] = AggregatedCriterionTruth(
                        criterion=norm_crit, requirements={}
                    )

                for req in atomic.requirements:
                    norm_req = req.requirement_type.strip().lower()
                    if norm_req not in agg_table.criteria[norm_crit].requirements:
                        agg_table.criteria[norm_crit].requirements[norm_req] = (
                            AggregatedRequirementTruth(
                                requirement_type=norm_req, groups={}
                            )
                        )

                    key = str(req.expected_value)
                    groups = agg_table.criteria[norm_crit].requirements[norm_req].groups
                    if key not in groups:
                        groups[key] = EvaluationGroup(
                            expected_value=req.expected_value,
                            trial_ids=[trial_id],
                            truth_value=TruthValue.UNKNOWN,
                        )
                    elif trial_id not in groups[key].trial_ids:
                        groups[key].trial_ids.append(trial_id)

    # After creating the aggregator
    criterion_count = len(agg_table.criteria)
    total_requirements = sum(
        len(crit.requirements) for crit in agg_table.criteria.values()
    )
    logging.info(
        "Aggregator contains %d criteria and %d requirements",
        criterion_count,
        total_requirements,
    )

    return agg_table
