# patient_matching/truth_evaluator.py
"""
This module updates the aggregated truth table based on a single parsed user response.
For each (criterion, requirement_type) pair in the user response, it uses direct dictionary lookups
to locate matching groups (each group represents trials sharing the same expected value) in the aggregated truth table.
For each group, it evaluates the user's input by sending the serialized representations to an LLM.
The LLM returns a structured response (llmEvaluation), whose 'evaluation' field is used to update the group's truth_value.
"""

import logging

from patient_matching.aggregated_trial_truth import (
    AggregatedTruthTable,
    TruthValue,
)
from patient_matching.user_answer_parser import ParsedCriterion
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from src.models.identified_criteria import ExpectedValueType  # , LLMNumericalComparison
from src.utils.config import TEMPERATURE, TIMEOUT
from src.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)


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
                    # Debug: log types and values before conversion
                    logger.debug(
                        "Before evaluate_expected_value: group.expected_value type=%s value=%r, response.user_value type=%s value=%r",
                        type(group.expected_value),
                        group.expected_value,
                        type(response.user_value),
                        response.user_value,
                    )
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


# def evaluate_numerical_comparison(
#     expected_value: Any,
#     user_value: Any,
# ) -> EvaluationResult:
#     """
#     Evaluates two LLMNumericalComparison objects if their units match.
#     Returns an EvaluationResult. If units do not match, returns None.
#     """
#     # Only handle EQUAL_TO for now, can expand as needed
#     if expected_value.operator == user_value.operator == "=":
#         match = user_value.value == expected_value.value
#     elif expected_value.operator == user_value.operator == "<":
#     eval_val = TruthValue.TRUE if match else TruthValue.FALSE
#     explanation = (
#         f"Numerical comparison: expected {expected_value.value} {expected_value.unit}, "
#         f"user provided {user_value.value} {user_value.unit}, "
#         f"{'match' if match else 'mismatch'}."
#     )
#     return EvaluationResult(explanation=explanation, evaluation=eval_val)


def evaluate_expected_value(
    expected_value: ExpectedValueType,
    user_value: ExpectedValueType,
    requirement_type: str,
    criterion: str,
) -> EvaluationResult:
    # Debug: log types and values at entry
    logger.debug(
        "IN evaluate_expected_value: expected_value type=%s value=%r, user_value type=%s value=%r",
        type(expected_value),
        expected_value,
        type(user_value),
        user_value,
    )
    """
    Evaluates whether the user_value satisfies the expected_value for the given requirement type.
    Dispatches to the appropriate evaluator based on type.
    """

    if isinstance(expected_value, bool) and isinstance(user_value, bool):
        logger.debug(
            "Directly evaluating boolean: expected_value=%s, user_value=%s",
        )
        return evaluate_bool_values(expected_value, user_value)
    # elif (
    #     isinstance(expected_value, LLMNumericalComparison)
    #     and isinstance(user_value, LLMNumericalComparison)
    #     and expected_value.unit.strip().lower() == user_value.unit.strip().lower()
    # ):
    #     logger.debug(
    #         "Directly evaluating LLMNumericalComparison: expected_value=%r, user_value=%r",
    #         expected_value,
    #         user_value,
    #     )
    #     result = evaluate_numerical_comparison(expected_value, user_value)
    #     if result is not None:
    #         return result
    # Fallback to LLM evaluation for other types or mismatched units
    expected_str = str(expected_value)
    user_str = str(user_value)
    return evaluate_value_with_llm(expected_str, user_str, requirement_type, criterion)


def evaluate_value_with_llm(
    expected_str: str, user_str: str, requirement_type: str, criterion: str
) -> EvaluationResult:
    # Debug: log types and values at entry
    logger.debug(
        "IN evaluate_value_with_llm: expected_str type=%s value=%r, user_str type=%s value=%r",
        type(expected_str),
        expected_str,
        type(user_str),
        user_str,
    )
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
