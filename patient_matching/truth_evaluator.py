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


def update_truth_table_with_user_response(
    user_response: ParsedCriterion, agg_table: AggregatedTruthTable
) -> set[str]:
    """
    Given a single parsed user response (ParsedCriterion) and the current aggregated truth table,
    uses direct dictionary lookups to locate matching groups and update their truth values by calling
    evaluate_value_with_llm().

    Returns a set of trial IDs that were modified.
    """
    modified_trial_ids: set = set()
    norm_crit = user_response.criterion.strip().lower()
    if norm_crit not in agg_table.criteria:
        logger.warning("Criterion '%s' not found in aggregated truth table.", norm_crit)
        return modified_trial_ids

    agg_criterion = agg_table.criteria[norm_crit]

    for response in user_response.responses:
        norm_req = response.requirement_type.strip().lower()
        if norm_req not in agg_criterion.requirements:
            logger.warning(
                "Requirement type '%s' for criterion '%s' not found.",
                norm_req,
                norm_crit,
            )
            continue

        agg_requirement = agg_criterion.requirements[norm_req]
        # Iterate over each group in the requirement mapping
        for key, group in agg_requirement.groups.items():
            # Evaluate the group's expected value against the user value
            eval_obj = evaluate_expected_value(
                str(group.expected_value), str(response.user_value), norm_req, norm_crit
            )
            group.truth_value = eval_obj.evaluation
            # Add all trial IDs in this group to the modified set
            modified_trial_ids.update(group.trial_ids)
            logger.info(
                "Updated group for '%s' (%s) with expected value '%s': %s (Explanation: %s)",
                norm_crit,
                norm_req,
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
