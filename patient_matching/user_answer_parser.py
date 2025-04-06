# patient_matching/user_answer_parser.py
import logging
from typing import List, Union

from pydantic import BaseModel, Field

from src.repositories.trial_repository import export_pydantic_to_json
from src.utils.config import TEMPERATURE, TIMEOUT
from src.utils.openai_client import get_openai_client

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Pydantic models for parsed user answer history
# -----------------------------------------------------------------------------


class RequirementResponse(BaseModel):
    requirement_type: str = Field(
        ..., description="The type of requirement (e.g., 'minimum', 'status')."
    )
    user_value: Union[str, int, float, bool] = Field(
        ..., description="The value provided by the user."
    )


class ParsedCriterion(BaseModel):
    criterion: str = Field(
        ..., description="The name of the criterion (e.g., 'age', 'lung status')."
    )
    responses: List[RequirementResponse] = Field(
        ..., description="List of responses for this criterion."
    )


class UserAnswerHistory(BaseModel):
    question: str = Field(..., description="The question asked to the user.")
    parsed_answers: List[ParsedCriterion] = Field(
        ..., description="The parsed criteria and responses from the user's answer."
    )
    # You may add a timestamp or other metadata fields later if needed


# -----------------------------------------------------------------------------
# LLM parsing functions
# -----------------------------------------------------------------------------


def parse_user_response(user_input: str, question: str) -> UserAnswerHistory:
    """
    Calls an LLM (using OpenAI) to parse the user's free text response into a structured
    UserAnswerHistory object containing a list of ParsedCriterion objects.
    """
    client = get_openai_client()

    prompt = (
        "You are an expert in parsing patient responses for clinical trial eligibility. "
        "Given the following question and the user's response, extract all the criteria mentioned "
        "along with their requirement types and provided values. The output should be valid JSON corresponding "
        "to a list of objects with the following format:\n\n"
        "{\n"
        '  "criterion": "<criterion_name>",\n'
        '  "responses": [\n'
        '      { "requirement_type": "<type>", "user_value": <value> },\n'
        "      ...\n"
        "  ]\n"
        "}\n\n"
        "Now, use this format to build a JSON object that also includes the original question. "
        "The final JSON should have the following structure:\n\n"
        "{\n"
        '  "question": "<the question>",\n'
        '  "parsed_answers": [\n'
        '      { "criterion": "...", "responses": [ { "requirement_type": "...", "user_value": ... }, ... ] },\n'
        "      ...\n"
        "  ]\n"
        "}\n\n"
        "Question: " + question + "\n"
        "User Response: " + user_input + "\n\n"
        "Provide your answer in valid JSON."
    )

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a patient response parser."},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            response_format=UserAnswerHistory,
            timeout=TIMEOUT,
        )

        if completion.choices[0].message.parsed:
            parsed_history = completion.choices[0].message.parsed
            return parsed_history
        else:
            logger.error("LLM did not return a parsable response.")
            raise ValueError(
                "LLM response could not be parsed into a UserAnswerHistory object."
            )
    except Exception as e:
        logger.error("Error during user response parsing: %s", e)
        raise ValueError(f"Error during user response parsing: {e}") from e


# -----------------------------------------------------------------------------
# Persistence function
# -----------------------------------------------------------------------------


def save_user_answer_history(history: UserAnswerHistory, file_name: str) -> bool:
    """
    Saves the UserAnswerHistory object to a JSON file using the existing export function.
    """
    # The export_pydantic_to_json function takes model, file_name, and folder as arguments.
    # We'll save to a folder named "user_data".
    folder = "user_data"
    return export_pydantic_to_json(history, file_name, folder)
