# patient_matching/aggregated_trial_truth.py
"""
This module defines a global aggregated truth table for clinical trial criteria.
Each entry groups a unique (criterion, requirement_type) pair along with a mapping of trial-specific
evaluation entries. Each evaluation entry holds the trial ID, the expected value for that trial,
and the truth value (initially UNKNOWN and later updated individually).

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


class TrialEvaluationEntry(BaseModel):
    """
    Represents a trial-specific evaluation entry for a given (criterion, requirement_type) pair.
    Stores the trial ID, the expected value, and the current truth value.
    """

    trial_id: str = Field(..., description="The clinical trial's NCT ID.")
    expected_value: ExpectedValueType = Field(
        ..., description="The expected value for this requirement in the trial."
    )
    truth_value: TruthValue = Field(
        TruthValue.UNKNOWN, description="The current truth value (default is UNKNOWN)."
    )


class AggregatedRequirementTruth(BaseModel):
    """
    Represents a requirement type for a given criterion.

    Redundancy Note: The 'requirement_type' field is stored here even though it is also used as the key in the parent dictionary.
    This is intentional for self-containment and ease of serialization.
    """

    requirement_type: str = Field(
        ..., description="The type of requirement (e.g., 'minimum', 'status')."
    )
    trial_evaluations: Dict[str, TrialEvaluationEntry] = Field(
        default_factory=dict, description="Mapping from trial ID to evaluation entry."
    )


class AggregatedCriterionTruth(BaseModel):
    """
    Represents a criterion with its aggregated requirement entries.

    Redundancy Note: The 'criterion' field is stored here even though it is used as the key in the top-level dictionary.
    This is intentional for self-containment and clarity.
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
    Groups them by the normalized criterion name and requirement type.
    Each group stores a mapping (dict) of trial IDs to TrialEvaluationEntry objects.

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
                # Normalize the criterion name for grouping
                norm_crit = atomic.criterion.strip().lower()
                # Ensure an AggregatedCriterionTruth exists for this criterion
                if norm_crit not in agg_table.criteria:
                    agg_table.criteria[norm_crit] = AggregatedCriterionTruth(
                        criterion=norm_crit, requirements={}
                    )

                # Process each requirement in the atomic criterion
                for req in atomic.requirements:
                    norm_req = req.requirement_type.strip().lower()
                    # Ensure an AggregatedRequirementTruth exists for this requirement type under the criterion
                    if norm_req not in agg_table.criteria[norm_crit].requirements:
                        agg_table.criteria[norm_crit].requirements[norm_req] = (
                            AggregatedRequirementTruth(
                                requirement_type=norm_req, trial_evaluations={}
                            )
                        )

                    # Add the trial evaluation entry if not already present for this trial
                    if (
                        trial_id
                        not in agg_table.criteria[norm_crit]
                        .requirements[norm_req]
                        .trial_evaluations
                    ):
                        entry = TrialEvaluationEntry(
                            trial_id=trial_id,
                            expected_value=req.expected_value,
                            truth_value=TruthValue.UNKNOWN,
                        )
                        agg_table.criteria[norm_crit].requirements[
                            norm_req
                        ].trial_evaluations[trial_id] = entry
                    else:
                        # Log a warning if a duplicate trial evaluation entry is encountered
                        logger.warning(
                            f"Duplicate trial evaluation entry detected for trial_id={trial_id}, "
                            f"criterion={norm_crit}, requirement_type={norm_req}. Skipping addition."
                        )

    return agg_table
