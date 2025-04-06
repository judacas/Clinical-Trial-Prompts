# patient_matching/truth_evaluator.py
"""
This module updates the aggregated truth table based on a single parsed user response.
For each (criterion, requirement type) pair in the user response, it locates matching entries
in the aggregated truth table (using O(1) dictionary lookups) and, for each trial's expected value,
evaluates the user's input by sending the serialized Pydantic representations of both the expected value
and user value to an LLM. The LLM returns a verdict ("true" or "false"), which is used to update the truth value.
"""

import logging
from typing import Any

from patient_matching.aggregated_trial_truth import (
    AggregatedCriterionTruth,
    AggregatedTruthTable,
    TruthValue,
)
from patient_matching.user_answer_parser import ParsedCriterion
from pydantic import BaseModel, Field

from src.models.identified_criteria import ExpectedValueType
from src.utils.config import TEMPERATURE, TIMEOUT
from src.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)


def update_truth_table_with_user_response(
    user_response: ParsedCriterion, agg_table: AggregatedTruthTable
) -> AggregatedTruthTable:
    """
    Given a single parsed user response (ParsedCriterion) and the current aggregated truth table,
    find matching entries (by criterion and requirement type) using direct dictionary lookups,
    and update each trial evaluation entry by calling evaluate_expected_value() which uses an LLM.

    Returns the updated AggregatedTruthTable.
    """
    # Normalize the criterion from user response.
    norm_crit = user_response.criterion.strip().lower()
    if norm_crit not in agg_table.criteria:
        logger.warning(
            "Criterion '%s' not found in the aggregated truth table.", norm_crit
        )
        return agg_table

    agg_criterion: AggregatedCriterionTruth = agg_table.criteria[norm_crit]

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
        for trial_id, trial_eval in agg_requirement.trial_evaluations.items():
            truth = evaluate_expected_value(
                agg_criterion.criterion,
                trial_eval.expected_value,
                response.user_value,
                norm_req,
            )
            trial_eval.truth_value = truth
            logger.info(
                "Updated '%s' (%s) for trial %s: %s",
                norm_crit,
                norm_req,
                trial_id,
                truth,
            )
    return agg_table


def evaluate_expected_value(
    criterion: str,
    expected_value: ExpectedValueType,
    user_value: Any,
    requirement_type: str,
) -> TruthValue:
    """
    Evaluates whether the user_value satisfies the expected_value for the given requirement type.
    Both expected_value and user_value are converted to their formatted Pydantic string representation,
    then provided to the LLM, which returns 'true' or 'false'.

    Future optimizations may replace the LLM call with direct rule-based evaluation for numeric or Boolean comparisons.
    hence why even though it looks like this function is not necessary, it is for future extensibility.
    """

    expected_str = str(expected_value)
    user_str = str(user_value)
    return evaluate_value_with_llm(
        criterion, expected_str, user_str, requirement_type
    ).evaluation


class llmEvaluation(BaseModel):
    """
    Represents the response from the LLM evaluation.
    """

    explanation: str = Field(..., description="Explanation of your thought process.")
    evaluation: TruthValue = Field(
        ...,
        description="Evaluation result: true, false, or unknown. Unknown if the LLM cannot determine the truth value from only the information given, do not try and pick true or false unless you are certain.",
    )


def evaluate_value_with_llm(
    criterion: str, expected_str: str, user_str: str, requirement_type: str
) -> llmEvaluation:
    """
    Calls an LLM to evaluate whether the user value satisfies the expected value.
    Both values are provided in their serialized (Pydantic-formatted) form.
    The prompt instructs the LLM to act as an expert clinical trial evaluator and respond with 'true' or 'false'.

    Returns TruthValue.TRUE if the LLM responds with "true", TruthValue.FALSE if "false",
    or TruthValue.UNKNOWN otherwise.
    """
    client = get_openai_client()

    prompt = (
        "You are an expert evaluator for clinical trial eligibility criteria.\n"
        "Your task is to determine if the user's value satisfies the expected value for a given criterion.\n\n"
        "Here are the details:\n\n"
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
