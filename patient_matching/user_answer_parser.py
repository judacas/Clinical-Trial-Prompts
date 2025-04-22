# patient_matching/user_answer_parser.py
import logging
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from src.models.identified_criteria import ExpectedValueType
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
    user_value: ExpectedValueType = Field(
        ..., description="The value provided by the user."
    )


class ParsedCriterion(BaseModel):
    criterion: str = Field(
        ..., description="The name of the criterion (e.g., 'age', 'lung status')."
    )
    responses: List[RequirementResponse] = Field(
        ..., description="List of responses for this criterion."
    )


# ? Does the LLM need to return the question or how will that be handled?
class LLMResponse(BaseModel):
    """
    The format that the LLM will return, without any timestamp fields.
    This is used for parsing the OpenAI response.
    """

    question: str = Field(..., description="The question asked to the user.")
    parsed_answers: List[ParsedCriterion] = Field(
        ..., description="The parsed criteria and responses from the user's answer."
    )


class UserAnswerHistory(BaseModel):
    """
    Internal model that includes timestamp information.
    Can be constructed from an LLMResponse.
    """

    question: str = Field(..., description="The question asked to the user.")
    parsed_answers: List[ParsedCriterion] = Field(
        ..., description="The parsed criteria and responses from the user's answer."
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When this answer was recorded"
    )

    @classmethod
    def from_llm_response(cls, llm_response: LLMResponse) -> "UserAnswerHistory":
        """
        Creates a UserAnswerHistory from an LLMResponse, adding the timestamp.
        """
        return cls(
            question=llm_response.question, parsed_answers=llm_response.parsed_answers
        )


class ConversationHistory(BaseModel):
    """
    Stores the complete history of a conversation, including all question-answer pairs
    and their timestamps.
    """

    start_time: datetime = Field(
        default_factory=datetime.now, description="When the conversation started"
    )
    conversation: List[UserAnswerHistory] = Field(
        default_factory=list,
        description="List of all question-answer pairs in the conversation",
    )

    def add_response(
        self, question: str, parsed_answers: List[ParsedCriterion]
    ) -> None:
        """
        Adds a new question-answer pair to the conversation history.
        """
        self.conversation.append(  # pylint: disable=E1101 this is because it assumes it to be a field type instead of list type so doesn't believe it has an append method incorrectly
            UserAnswerHistory(question=question, parsed_answers=parsed_answers)
        )


def parse_user_response(user_input: str, question: str) -> UserAnswerHistory:
    """
    Calls an LLM (using OpenAI) to parse the user's free text response into a structured
    UserAnswerHistory object containing a list of ParsedCriterion objects.
    """
    client = get_openai_client()

    prompt = (
        "You are an expert in parsing patient responses for clinical trial eligibility. "
        "Given the following question and the user's response, extract all the criteria mentioned "
        "along with their requirement types and provided values.\n\n"
        "Question: " + question + "\n"
        "User Response: " + user_input + "\n\n"
    )

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a patient response parser."},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            response_format=LLMResponse,
            timeout=TIMEOUT,
        )

        if completion.choices[0].message.parsed:
            llm_response = completion.choices[0].message.parsed
            return UserAnswerHistory.from_llm_response(llm_response)
        else:
            logger.error("LLM did not return a parsable response.")
            raise ValueError(
                "LLM response could not be parsed into a UserAnswerHistory object."
            )
    except Exception as e:
        logger.error("Error during user response parsing: %s", e)
        raise ValueError(f"Error during user response parsing: {e}") from e


def save_user_answer_history(history: UserAnswerHistory, file_name: str) -> bool:
    """
    Saves the UserAnswerHistory object to a JSON file using the existing export function.
    """
    # The export_pydantic_to_json function takes model, file_name, and folder as arguments.
    # We'll save to a folder named "user_data".
    folder = "user_data"
    return export_pydantic_to_json(history, file_name, folder)
