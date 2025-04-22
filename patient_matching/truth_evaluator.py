# patient_matching/truth_evaluator.py
"""
This module updates the aggregated truth table based on a single parsed user response.
For each (criterion, requirement_type) pair in the user response, it uses direct dictionary lookups
to locate matching groups (each group represents trials sharing the same expected value) in the aggregated truth table.
For each group, it evaluates the user's input by sending the serialized representations to an LLM.
The LLM returns a structured response (llmEvaluation), whose 'evaluation' field is used to update the group's truth_value.
"""

import logging
import operator

import pint
from patient_matching.aggregated_trial_truth import (
    AggregatedTruthTable,
    TruthValue,
)
from patient_matching.user_answer_parser import ParsedCriterion
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from src.models.identified_criteria import ExpectedValueType, LLMOperator
from src.utils.config import TEMPERATURE, TIMEOUT
from src.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)

op_map = {
    LLMOperator.GREATER_THAN: operator.gt,
    LLMOperator.LESS_THAN: operator.lt,
    LLMOperator.EQUAL_TO: operator.eq,
    LLMOperator.NOT_EQUAL_TO: operator.ne,
    LLMOperator.GREATER_THAN_OR_EQUAL_TO: operator.ge,
    LLMOperator.LESS_THAN_OR_EQUAL_TO: operator.le,
}


class EvaluationResult(BaseModel):
    """
    Generic result for any evaluation, containing an explanation and the evaluation value.
    """

    explanation: str = Field(..., description="Explanation of the evaluation result.")
    evaluation: TruthValue = Field(
        ..., description="Evaluation result: true, false, or unknown."
    )


def get_all_matches(
    query: str, choices: list[str], score_cutoff: int = 75
) -> list[str]:
    """
    Returns a list of matching strings from choices using fuzzy matching.
    Only includes matches with a score >= score_cutoff.
    """
    matches = process.extract(
        query, choices, scorer=fuzz.token_sort_ratio, score_cutoff=score_cutoff
    )
    return [match for match, score, _ in matches]


def find_candidate_criteria(
    norm_crit: str,
    norm_req: str,
    agg_table: AggregatedTruthTable,
    score_cutoff: int = 75,
) -> set[str]:
    """
    Finds candidate criterion keys for a given user criterion and requirement by:
    1. Exact match on criterion (C-C).
    2. Exact match on combined criterion + requirement (CRT-CRT).
    3. Fuzzy match combinations: C-C, CRT-C, CRT-CRT, C-CRT.
    """
    criteria_keys = list(agg_table.criteria.keys())
    # Map composite strings ("criterion requirement") to criterion keys
    comb_map = {
        f"{crit_key} {req_key}": crit_key
        for crit_key in criteria_keys
        for req_key in agg_table.criteria[crit_key].requirements.keys()
    }
    composite_keys = list(comb_map.keys())

    candidates: set[str] = set()
    # Exact C-C
    if norm_crit in agg_table.criteria:
        candidates.add(norm_crit)
    # Exact CRT-CRT
    combined = f"{norm_crit} {norm_req}"
    if combined in comb_map:
        candidates.add(comb_map[combined])
    # If exact match found, return immediately
    if candidates:
        return candidates

    # Fuzzy C-C
    candidates.update(get_all_matches(norm_crit, criteria_keys, score_cutoff))
    # Fuzzy CRT-C
    candidates.update(get_all_matches(combined, criteria_keys, score_cutoff))
    # Fuzzy CRT-CRT
    matched_composite = get_all_matches(combined, composite_keys, score_cutoff)
    candidates.update(comb_map[comp] for comp in matched_composite)
    # Fuzzy C-CRT
    matched_composite2 = get_all_matches(norm_crit, composite_keys, score_cutoff)
    candidates.update(comb_map[comp] for comp in matched_composite2)

    return candidates


def update_truth_table_with_user_response(
    user_response: ParsedCriterion, agg_table: AggregatedTruthTable
) -> set[str]:
    modified_trial_ids: set = set()
    # For each response in the user input
    for response in user_response.responses:
        norm_crit = user_response.criterion.strip().lower()
        norm_req = response.requirement_type.strip().lower()

        # Determine matching aggregated criteria (exact first, then fuzzy on C-C, CRT-C, CRT-CRT, C-CRT)
        candidate_criteria = find_candidate_criteria(norm_crit, norm_req, agg_table)
        if not candidate_criteria:
            logger.warning(
                "No matching aggregated criterion for response with criterion '%s' and requirement '%s'.",
                norm_crit,
                norm_req,
            )
            continue

        # For each candidate aggregated criterion, process all its requirement groups.
        for crit_key in candidate_criteria:
            agg_criterion = agg_table.criteria[crit_key]
            # Instead of fuzzy matching requirement, just consider every requirement in this criterion.
            for req_key, agg_requirement in agg_criterion.requirements.items():
                for key, group in agg_requirement.groups.items():
                    eval_obj = evaluate_expected_value(
                        group.expected_value,
                        response.user_value,
                        req_key,
                        crit_key,
                    )
                    group.truth_value = eval_obj.evaluation
                    modified_trial_ids.update(group.trial_ids)
                    logger.info(
                        "Updated group for '%s' (%s) with expected value '%s': %s (Explanation: %s)",
                        crit_key,
                        req_key,
                        key,
                        eval_obj.evaluation,
                        eval_obj.explanation,
                    )
    return modified_trial_ids


def evaluate_bool_values(
    expected_value: bool,
    user_value: bool,
) -> EvaluationResult:
    """
    Evaluates two boolean values for equality and returns an EvaluationResult.
    """
    match = user_value == expected_value
    eval_val = TruthValue.TRUE if match else TruthValue.FALSE
    explanation = (
        f"Boolean comparison: expected {expected_value}, "
        f"user provided {user_value}, "
        f"{'match' if match else 'mismatch'}."
    )
    return EvaluationResult(explanation=explanation, evaluation=eval_val)


def _convert_units(value, from_unit, to_unit):
    """
    Convert value from from_unit to to_unit if possible using pint.
    Returns (converted_value, True) if conversion is possible, else (original_value, False).
    """
    ureg = pint.UnitRegistry()
    from_unit = from_unit.strip().lower()
    to_unit = to_unit.strip().lower()
    if from_unit == to_unit:
        return value, True
    try:
        q = value * ureg(from_unit)
        converted = q.to(to_unit)
        return converted.magnitude, True
    except Exception as e:
        logger.warning(f"Unit conversion failed: {e}")
        return value, False


def is_stricter(user_op, user_val, expected_op, expected_val):
    """
    Returns True if the user's constraint is strictly stricter or as strict as the expected constraint,
    False if looser, and None if ambiguous or not handled.
    Handles both 'greater' and 'less' directions symmetrically.
    """
    directions = {
        "greater": {
            "ops": {LLMOperator.GREATER_THAN, LLMOperator.GREATER_THAN_OR_EQUAL_TO},
            "cmp": operator.ge,
            "boundary_strict": (
                LLMOperator.GREATER_THAN_OR_EQUAL_TO,
                LLMOperator.GREATER_THAN,
            ),
            "boundary_loose": (
                LLMOperator.GREATER_THAN,
                LLMOperator.GREATER_THAN_OR_EQUAL_TO,
            ),
        },
        "less": {
            "ops": {LLMOperator.LESS_THAN, LLMOperator.LESS_THAN_OR_EQUAL_TO},
            "cmp": operator.le,
            "boundary_strict": (
                LLMOperator.LESS_THAN_OR_EQUAL_TO,
                LLMOperator.LESS_THAN,
            ),
            "boundary_loose": (
                LLMOperator.LESS_THAN,
                LLMOperator.LESS_THAN_OR_EQUAL_TO,
            ),
        },
    }
    for props in directions.values():
        if expected_op in props["ops"] and user_op in props["ops"]:
            if props["cmp"](user_val, expected_val):  # type: ignore[operator]
                if user_val != expected_val:
                    return True
                # user_val == expected_val
                if (expected_op, user_op) == props["boundary_strict"]:
                    return True
                if (expected_op, user_op) == props["boundary_loose"]:
                    return False
                return True  # same operator and value
            else:
                return False
    return None  # ambiguous or not handled


def evaluate_numerical_comparison(
    expected_value,
    user_value,
) -> EvaluationResult:
    """
    Evaluates two LLMNumericalComparison objects.
    If units mismatch, attempts conversion.
    Returns UNKNOWN if logic is ambiguous.
    Assumes both arguments are LLMNumericalComparison.
    """

    # Convert units if needed
    exp_unit = expected_value.unit.strip().lower()
    user_unit = user_value.unit.strip().lower()
    exp_val = expected_value.value
    user_val = user_value.value

    if exp_unit != user_unit:
        converted_user_val, ok = _convert_units(user_val, user_unit, exp_unit)
        if not ok:
            explanation = f"Unit mismatch and cannot convert: expected '{exp_unit}', user provided '{user_unit}'."
            return EvaluationResult(
                explanation=explanation, evaluation=TruthValue.UNKNOWN
            )
        user_val = converted_user_val
        user_unit = exp_unit  # now units match

    # Now both values are in the same unit

    # Evaluate based on both expected and user operator
    # If both are EQUAL_TO, simple comparison
    if (
        expected_value.operator == LLMOperator.EQUAL_TO
        and user_value.operator == LLMOperator.EQUAL_TO
    ):
        match = user_val == exp_val
        eval_val = TruthValue.TRUE if match else TruthValue.FALSE
        explanation = (
            f"Numerical comparison: expected = {exp_val} {exp_unit}, user provided = {user_val} {user_unit}, "
            f"{'match' if match else 'mismatch'}."
        )
        return EvaluationResult(explanation=explanation, evaluation=eval_val)

    # If expected is a range (e.g., >5), check if user value satisfies it
    # If user operator is EQUAL_TO, treat as a value
    if user_value.operator == LLMOperator.EQUAL_TO:
        op_func = op_map.get(expected_value.operator)
        if op_func is not None:
            match = op_func(user_val, exp_val)
            eval_val = TruthValue.TRUE if match else TruthValue.FALSE
            explanation = (
                f"Numerical comparison: expected {expected_value.operator} {exp_val} {exp_unit}, "
                f"user provided = {user_val} {user_unit}, "
                f"{'satisfies' if match else 'does not satisfy'}."
            )
            return EvaluationResult(explanation=explanation, evaluation=eval_val)

    # Handle NOT_EQUAL_TO as a combination of < and >
    if expected_value.operator == LLMOperator.NOT_EQUAL_TO:
        less_result = evaluate_numerical_comparison(
            type(expected_value)(
                operator=LLMOperator.LESS_THAN,
                value=expected_value.value,
                unit=expected_value.unit,
            ),
            user_value,
        )
        greater_result = evaluate_numerical_comparison(
            type(expected_value)(
                operator=LLMOperator.GREATER_THAN,
                value=expected_value.value,
                unit=expected_value.unit,
            ),
            user_value,
        )
        if (
            less_result.evaluation == TruthValue.TRUE
            or greater_result.evaluation == TruthValue.TRUE
        ):
            explanation = f"User value is not equal to expected value: {less_result.explanation} OR {greater_result.explanation}"
            return EvaluationResult(explanation=explanation, evaluation=TruthValue.TRUE)
        if (
            less_result.evaluation == TruthValue.FALSE
            and greater_result.evaluation == TruthValue.FALSE
        ):
            explanation = "User value equals expected value."
            return EvaluationResult(
                explanation=explanation, evaluation=TruthValue.FALSE
            )
        explanation = "Cannot determine if user value is not equal to expected value."
        return EvaluationResult(explanation=explanation, evaluation=TruthValue.UNKNOWN)

    # If both have non-equal operators, use is_stricter for both directions
    stricter = is_stricter(
        user_value.operator, user_val, expected_value.operator, exp_val
    )
    if stricter is True:
        explanation = (
            f"User's threshold ({user_val} {user_unit}, {user_value.operator}) is as strict or stricter than expected "
            f"({exp_val} {exp_unit}, {expected_value.operator}), so satisfies."
        )
        return EvaluationResult(explanation=explanation, evaluation=TruthValue.TRUE)
    elif stricter is False:
        explanation = (
            f"User's threshold ({user_val} {user_unit}, {user_value.operator}) is less strict than expected "
            f"({exp_val} {exp_unit}, {expected_value.operator}), so does not satisfy."
        )
        return EvaluationResult(explanation=explanation, evaluation=TruthValue.FALSE)

    # Handle opposite direction: e.g., expected > 18, user < 18
    opposite_pairs = [
        (LLMOperator.GREATER_THAN, LLMOperator.LESS_THAN),
        (LLMOperator.GREATER_THAN, LLMOperator.LESS_THAN_OR_EQUAL_TO),
        (LLMOperator.GREATER_THAN_OR_EQUAL_TO, LLMOperator.LESS_THAN),
        (LLMOperator.GREATER_THAN_OR_EQUAL_TO, LLMOperator.LESS_THAN_OR_EQUAL_TO),
        (LLMOperator.LESS_THAN, LLMOperator.GREATER_THAN),
        (LLMOperator.LESS_THAN, LLMOperator.GREATER_THAN_OR_EQUAL_TO),
        (LLMOperator.LESS_THAN_OR_EQUAL_TO, LLMOperator.GREATER_THAN),
        (LLMOperator.LESS_THAN_OR_EQUAL_TO, LLMOperator.GREATER_THAN_OR_EQUAL_TO),
    ]
    if (expected_value.operator, user_value.operator) in opposite_pairs:
        # Check if the intervals do not overlap
        # For expected > a, user < b: if b <= a, then no overlap
        if expected_value.operator in (
            LLMOperator.GREATER_THAN,
            LLMOperator.GREATER_THAN_OR_EQUAL_TO,
        ):
            if user_val <= exp_val:
                explanation = f"User's threshold ({user_value.operator} {user_val}) does not overlap with expected ({expected_value.operator} {exp_val}), so does not satisfy."
                return EvaluationResult(
                    explanation=explanation, evaluation=TruthValue.FALSE
                )
        # For expected < a, user > b: if b >= a, then no overlap
        if expected_value.operator in (
            LLMOperator.LESS_THAN,
            LLMOperator.LESS_THAN_OR_EQUAL_TO,
        ):
            if user_val >= exp_val:
                explanation = f"User's threshold ({user_value.operator} {user_val}) does not overlap with expected ({expected_value.operator} {exp_val}), so does not satisfy."
                return EvaluationResult(
                    explanation=explanation, evaluation=TruthValue.FALSE
                )
        # Otherwise, intervals overlap, so unknown
        explanation = f"User's threshold ({user_value.operator} {user_val}) and expected ({expected_value.operator} {exp_val}) overlap; cannot determine."
        return EvaluationResult(explanation=explanation, evaluation=TruthValue.UNKNOWN)

    # If logic is ambiguous or not handled, return UNKNOWN
    explanation = (
        f"Cannot determine truth value for expected '{expected_value.operator} {exp_val} {exp_unit}' "
        f"and user '{user_value.operator} {user_val} {user_unit}'."
    )
    return EvaluationResult(explanation=explanation, evaluation=TruthValue.UNKNOWN)


def evaluate_expected_value(
    expected_value: ExpectedValueType,
    user_value: ExpectedValueType,
    requirement_type: str,
    criterion: str,
) -> EvaluationResult:
    """
    Evaluates whether the user_value satisfies the expected_value for the given requirement type.
    Dispatches to the appropriate evaluator based on type.
    """
    from src.models.identified_criteria import LLMNumericalComparison, LLMRange

    if isinstance(expected_value, bool) and isinstance(user_value, bool):
        logger.debug(
            "Directly evaluating boolean: expected_value=%s, user_value=%s",
        )
        return evaluate_bool_values(expected_value, user_value)
    elif isinstance(expected_value, LLMNumericalComparison) and isinstance(
        user_value, LLMNumericalComparison
    ):
        logger.debug(
            "Directly evaluating LLMNumericalComparison: expected_value=%r, user_value=%r",
            expected_value,
            user_value,
        )
        return evaluate_numerical_comparison(expected_value, user_value)
    elif isinstance(expected_value, LLMRange):
        return evaluate_llm_range(expected_value, user_value)
    # Fallback to LLM evaluation for other types or mismatched units
    expected_str = str(expected_value)
    user_str = str(user_value)
    logger.warning(
        "Falling back to LLM evaluation: expected_str=%s, user_str=%s",
        expected_str,
        user_str,
    )
    return evaluate_value_with_llm(expected_str, user_str, requirement_type, criterion)


def evaluate_value_with_llm(
    expected_str: str, user_str: str, requirement_type: str, criterion: str
) -> EvaluationResult:
    logger.debug(
        "Evaluating with LLM: expected_str=%s, user_str=%s", expected_str, user_str
    )
    """
    Calls an LLM to evaluate whether the user value satisfies the expected value.
    Both values are provided in their serialized form.

    The prompt instructs the LLM to act as an expert clinical trial evaluator and to return a JSON object
    matching the llmEvaluation schema. The JSON should contain 'explanation' and 'evaluation' fields.

    Returns an llmEvaluation object.
    """
    client = get_openai_client()

    prompt = (
        "You are an expert evaluator for clinical trial eligibility criteria.\n"
        "Below are structured inputs in a Pydantic-like format.\n\n"
        "Criterion:\n"
        f"{criterion}\n\n"
        "Expected Value (from the trial):\n"
        f"{expected_str}\n\n"
        "Requirement Type:\n"
        f"{requirement_type}\n\n"
    )
    user_str = f"User Value (provided by the patient):\n{user_str}\n\n"

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {"role": "user", "content": user_str},
            ],
            temperature=TEMPERATURE,
            response_format=EvaluationResult,
            timeout=TIMEOUT,
        )
        if response := completion.choices[0].message.parsed:
            logger.debug("LLM evaluation response: %s", response)
            return response
        else:
            logger.warning("Failed to parse LLM evaluation response.")
            raise ValueError("Failed to parse LLM evaluation response.")

    except Exception as e:
        logger.error("LLM evaluation failed: %s", e)
        raise ValueError(f"LLM evaluation failed: {e}") from e


def evaluate_llm_range(expected_range, user_value) -> EvaluationResult:
    """
    Evaluates an LLMRange by evaluating all its LLMNumericalComparison objects against the user value.
    If all are TRUE, return TRUE; if any are FALSE, return FALSE; otherwise, UNKNOWN.
    """
    results = []
    for comp in expected_range.comparisons:
        res = evaluate_numerical_comparison(comp, user_value)
        results.append(res.evaluation)
    if all(r == TruthValue.TRUE for r in results):
        return EvaluationResult(
            explanation="All range comparisons satisfied.", evaluation=TruthValue.TRUE
        )
    if any(r == TruthValue.FALSE for r in results):
        return EvaluationResult(
            explanation="At least one range comparison not satisfied.",
            evaluation=TruthValue.FALSE,
        )
    return EvaluationResult(
        explanation="Range comparison result is ambiguous.",
        evaluation=TruthValue.UNKNOWN,
    )
