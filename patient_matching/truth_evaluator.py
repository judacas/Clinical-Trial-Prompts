# patient_matching/truth_evaluator.py
"""
This module updates the aggregated truth table based on a single parsed user response.
For each (criterion, requirement_type) pair in the user response, it uses direct dictionary lookups
to locate matching groups (each group represents trials sharing the same expected value) in the aggregated truth table.
For each group, it evaluates the user's input by sending the serialized representations to an LLM.
The LLM returns a structured response (llmEvaluation), whose 'evaluation' field is used to update the group's truth_value.
"""

import logging
from typing import Any

from patient_matching.aggregated_trial_truth import (
    AggregatedTruthTable,
    TruthValue,
)
from patient_matching.user_answer_parser import ParsedCriterion
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from src.models.identified_criteria import ExpectedValueType
from src.utils.config import TEMPERATURE, TIMEOUT
from src.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)


class llmEvaluation(BaseModel):
    """
    Represents the response from the LLM evaluation.
    """

    explanation: str = Field(..., description="Explanation of your thought process.")
    evaluation: TruthValue = Field(
        ...,
        description="Evaluation result: true, false, or unknown. Unknown if the LLM cannot determine the truth value.",
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


def update_truth_table_with_user_response(
    user_response: ParsedCriterion, agg_table: AggregatedTruthTable
) -> set[str]:
    modified_trial_ids: set = set()
    # For each response in the user input
    for response in user_response.responses:
        norm_crit = user_response.criterion.strip().lower()
        norm_req = response.requirement_type.strip().lower()
        combo = norm_crit + " " + norm_req

        candidate_criteria = set()

        # Stage 1: Fuzzy match criterion alone.
        candidates1 = get_all_matches(norm_crit, list(agg_table.criteria.keys()))
        candidate_criteria.update(candidates1)

        # Stage 2: Fuzzy match combined (criterion + requirement) against criteria names.
        for crit_key in agg_table.criteria.keys():
            if fuzz.token_sort_ratio(combo, crit_key) >= 75:
                candidate_criteria.add(crit_key)

        # Stage 3: Fuzzy match combined (criterion + requirement) against each "criterion key + requirement key".
        for crit_key, crit_obj in agg_table.criteria.items():
            for req_key in crit_obj.requirements.keys():
                comb_str = crit_key + " " + req_key
                if fuzz.token_sort_ratio(combo, comb_str) >= 75:
                    candidate_criteria.add(crit_key)

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
                        str(group.expected_value),
                        str(response.user_value),
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


def evaluate_expected_value(
    expected_value: ExpectedValueType,
    user_value: Any,
    requirement_type: str,
    criterion: str,
) -> llmEvaluation:
    """
    Evaluates whether the user_value satisfies the expected_value for the given requirement type.
    Both expected_value and user_value are converted to strings and then provided to the LLM,
    which returns a structured response conforming to the llmEvaluation schema.
    """
    expected_str = str(expected_value)
    user_str = str(user_value)
    return evaluate_value_with_llm(expected_str, user_str, requirement_type, criterion)


def evaluate_value_with_llm(
    expected_str: str, user_str: str, requirement_type: str, criterion: str
) -> llmEvaluation:
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
            response_format=llmEvaluation,
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
