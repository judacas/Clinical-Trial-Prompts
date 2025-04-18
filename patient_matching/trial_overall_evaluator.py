# patient_matching/trial_overall_evaluator.py
"""
This module evaluates the overall eligibility (truth value) for each trial based on its logical structure
and the updated aggregated truth table.

It uses three-valued logic (TRUE, FALSE, UNKNOWN) to combine the truth values of atomic criteria (looked up from
the aggregator) according to the logical operators stored in the LogicalTrial.
Logical operators handled include AND, OR, NOT, XOR, and CONDITIONAL.
Each operator is now evaluated by a dedicated function that takes the entire structure rather than precomputed truth values.
"""

import logging
from typing import Any, Callable, Dict, List

# Import aggregated truth table and its models
from patient_matching.aggregated_trial_truth import AggregatedTruthTable, TruthValue
from pydantic import BaseModel, Field

# Import logical models (from logical_criteria.py / logical_structurizer.py)
from src.models.logical_criteria import (
    LLMLogicalAnd,
    LLMLogicalConditional,
    LLMLogicalNot,
    LLMLogicalOr,
    LLMLogicalXor,
    LogicalTrial,
    SingleRequirementCriterion,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Three-Valued Logic Functions for Operator Combination
# ---------------------------------------------------------------------------
def combine_and(values: List[TruthValue]) -> TruthValue:
    if any(val == TruthValue.FALSE for val in values):
        return TruthValue.FALSE
    if any(val == TruthValue.UNKNOWN for val in values):
        return TruthValue.UNKNOWN
    return TruthValue.TRUE


def combine_or(values: List[TruthValue]) -> TruthValue:
    if any(val == TruthValue.TRUE for val in values):
        return TruthValue.TRUE
    if any(val == TruthValue.UNKNOWN for val in values):
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


def combine_xor(values: List[TruthValue]) -> TruthValue:
    if any(val == TruthValue.UNKNOWN for val in values):
        return TruthValue.UNKNOWN
    true_count = sum(1 for val in values if val == TruthValue.TRUE)
    return TruthValue.TRUE if true_count % 2 == 1 else TruthValue.FALSE


# ---------------------------------------------------------------------------
# Operator-Specific Evaluation Functions
# ---------------------------------------------------------------------------
def eval_and(
    and_struct: LLMLogicalAnd, trial_id: str, agg_table: AggregatedTruthTable
) -> TruthValue:
    sub_values = [
        evaluate_logical_structure_for_trial(sub, trial_id, agg_table)
        for sub in and_struct.and_criteria
    ]
    return combine_and(sub_values)


def eval_or(
    or_struct: LLMLogicalOr, trial_id: str, agg_table: AggregatedTruthTable
) -> TruthValue:
    sub_values = [
        evaluate_logical_structure_for_trial(sub, trial_id, agg_table)
        for sub in or_struct.or_criteria
    ]
    return combine_or(sub_values)


def negate(value: TruthValue) -> TruthValue:
    """
    Negates the truth value.
    """
    if value == TruthValue.TRUE:
        return TruthValue.FALSE
    elif value == TruthValue.FALSE:
        return TruthValue.TRUE
    else:
        return TruthValue.UNKNOWN


def eval_not(
    not_struct: LLMLogicalNot, trial_id: str, agg_table: AggregatedTruthTable
) -> TruthValue:
    sub_value = evaluate_logical_structure_for_trial(
        not_struct.not_criteria, trial_id, agg_table
    )
    return negate(sub_value)


def eval_xor(
    xor_struct: LLMLogicalXor, trial_id: str, agg_table: AggregatedTruthTable
) -> TruthValue:
    sub_values = [
        evaluate_logical_structure_for_trial(sub, trial_id, agg_table)
        for sub in xor_struct.xor_criteria
    ]
    return combine_xor(sub_values)


def eval_conditional(
    cond_struct: LLMLogicalConditional, trial_id: str, agg_table: AggregatedTruthTable
) -> TruthValue:
    condition_val = evaluate_logical_structure_for_trial(
        cond_struct.condition, trial_id, agg_table
    )
    if condition_val == TruthValue.TRUE:
        # If the condition is true and then_criteria exists, evaluate it; if not, default to TRUE.
        if cond_struct.then_criteria is not None:
            return evaluate_logical_structure_for_trial(
                cond_struct.then_criteria, trial_id, agg_table
            )
        else:
            return TruthValue.TRUE
    elif condition_val == TruthValue.FALSE:
        # If the condition is false and else_criteria exists, evaluate it; if not, default to TRUE.
        if cond_struct.else_criteria is not None:
            return evaluate_logical_structure_for_trial(
                cond_struct.else_criteria, trial_id, agg_table
            )
        else:
            return TruthValue.TRUE
    else:
        return TruthValue.UNKNOWN


# ---------------------------------------------------------------------------
# Mapping from operator type to its evaluation function
# ---------------------------------------------------------------------------
OperatorEvaluator = Callable[[Any, str, AggregatedTruthTable], TruthValue]

operator_map: Dict[type, OperatorEvaluator] = {
    LLMLogicalAnd: eval_and,
    LLMLogicalOr: eval_or,
    LLMLogicalNot: eval_not,
    LLMLogicalXor: eval_xor,
    LLMLogicalConditional: eval_conditional,
}


# ---------------------------------------------------------------------------
# Recursive Overall Evaluation Function
# ---------------------------------------------------------------------------
def evaluate_logical_structure_for_trial(
    structure: Any, trial_id: str, agg_table: AggregatedTruthTable
) -> TruthValue:
    """
    Recursively evaluates a trial's logical structure for a given trial_id.

    For an atomic criterion (SingleRequirementCriterion), it looks up the truth value in the aggregator.
    For a logical operator, it uses the corresponding operator function from operator_map.
    """
    # Atomic criterion
    if isinstance(structure, SingleRequirementCriterion):
        norm_crit = structure.criterion.strip().lower()
        norm_req = structure.requirement.requirement_type.strip().lower()
        key = str(structure.requirement.expected_value)
        try:
            group = agg_table.criteria[norm_crit].requirements[norm_req].groups[key]
            if trial_id in group.trial_ids:
                return group.truth_value
            else:
                return TruthValue.UNKNOWN
        except KeyError:
            logger.warning(
                "Aggregator lookup failed for criterion '%s', requirement '%s', key '%s' for trial %s.",
                norm_crit,
                norm_req,
                key,
                trial_id,
            )
            return TruthValue.UNKNOWN

    # Logical operators: use our operator_map to delegate evaluation
    for op_type, evaluator in operator_map.items():
        if isinstance(structure, op_type):
            return evaluator(structure, trial_id, agg_table)

    logger.error("Unrecognized logical structure type: %s", type(structure))
    return TruthValue.UNKNOWN


# ---------------------------------------------------------------------------
# Overall Trial Evaluation Models and Wrappers
# ---------------------------------------------------------------------------
class TrialOverallTruth(BaseModel):
    """
    Represents the overall evaluation for a trial.
    """

    trial_id: str = Field(..., description="The clinical trial's NCT ID.")
    overall_truth: TruthValue = Field(
        ...,
        description="Overall eligibility: TRUE if eligible, FALSE if not, UNKNOWN otherwise.",
    )


def evaluate_trial_overall(
    logical_trial: LogicalTrial, agg_table: AggregatedTruthTable
) -> TrialOverallTruth:
    """
    Evaluates the overall eligibility of a trial by combining eligible and ineligible criteria.

    Evaluates a trial by AND-ing together all inclusion and miscellaneous lines,
    and then AND-ing that with the negation of the OR combination of exclusion lines.
    Failed lines are no longer included in the evaluation to avoid potential problems.

    Returns early with FALSE if any critical condition fails.

    Returns a TrialOverallTruth object with the trial's NCT ID and its overall truth value.
    """
    trial_id = logical_trial.info.nct_id

    # Combine positive criteria lines (inclusions and miscellaneous only)
    positive_lines = logical_trial.inclusion_lines + logical_trial.miscellaneous_lines
    positive_values: List[TruthValue] = []
    for line in positive_lines:
        # Each LogicalLine has a 'logical_structure' that we evaluate
        value = evaluate_logical_structure_for_trial(
            line.logical_structure, trial_id, agg_table
        )
        if value == TruthValue.FALSE:
            return TrialOverallTruth(
                trial_id=trial_id, overall_truth=TruthValue.FALSE
            )  # Early termination if any inclusion fails
        positive_values.append(value)
    positive_combined = (
        combine_and(positive_values) if positive_values else TruthValue.UNKNOWN
    )
    if positive_combined == TruthValue.FALSE:
        return TrialOverallTruth(
            trial_id=trial_id, overall_truth=TruthValue.FALSE
        )  # Early termination if combined positive criteria fails

    # Combine negative criteria lines (exclusions only)
    negative_lines = logical_trial.exclusion_lines
    negative_values: List[TruthValue] = []
    for line in negative_lines:
        value = evaluate_logical_structure_for_trial(
            line.logical_structure, trial_id, agg_table
        )
        if value == TruthValue.TRUE:
            return TrialOverallTruth(
                trial_id=trial_id, overall_truth=TruthValue.FALSE
            )  # Early termination if any exclusion is true
        negative_values.append(value)
    negative_combined = (
        combine_or(negative_values) if negative_values else TruthValue.FALSE
    )

    overall_value = combine_and([positive_combined, negate(negative_combined)])
    return TrialOverallTruth(trial_id=trial_id, overall_truth=overall_value)


def filter_ineligible_trials(
    logical_trials: List[LogicalTrial], agg_table: AggregatedTruthTable
) -> List[LogicalTrial]:
    """
    Filters out trials that are determined to be ineligible (FALSE) or unknown (UNKNOWN).
    Only returns trials that are definitely eligible (TRUE).

    Args:
        logical_trials: List of LogicalTrial objects to evaluate
        agg_table: AggregatedTruthTable containing the current truth values

    Returns:
        List of LogicalTrial objects that are still eligible
    """
    eligible_trials = []
    for trial in logical_trials:
        result = evaluate_trial_overall(trial, agg_table)
        if result.overall_truth in [TruthValue.TRUE, TruthValue.UNKNOWN]:
            eligible_trials.append(trial)
        else:
            logger.info(
                "Trial %s filtered out due to %s eligibility status",
                trial.info.nct_id,
                result.overall_truth,
            )
    return eligible_trials


def evaluate_all_trials(
    logical_trials: List[LogicalTrial], agg_table: AggregatedTruthTable
) -> List[TrialOverallTruth]:
    """
    Evaluates the overall eligibility of each trial in a list of LogicalTrial objects.
    Returns a list of TrialOverallTruth objects.
    """
    results = []
    for trial in logical_trials:
        result = evaluate_trial_overall(trial, agg_table)
        results.append(result)
        logger.info(
            "Trial %s overall evaluation: %s", trial.info.nct_id, result.overall_truth
        )
    return results
