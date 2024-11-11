# services/criterion_evaluator.py

import logging
from typing import Optional, List
from models.criterion import AtomicCriterion, Category
from pydantic import BaseModel, Field
from utils.openai_client import get_openai_client

# Configure logging
logger = logging.getLogger(__name__)

client = get_openai_client()

class LLMResponse(BaseModel):
    """
    Represents the LLM's response.
    """
    continueAsking: bool = Field(..., description="true if the llm needs to clarify something. False if it can determine eligibility.")
    satisfied: Optional[bool] = Field(
        ..., description="Whether the user satisfies the criterion."
    )
    reasoning: Optional[str] = Field(
        ..., description="Explanation of the decision."
    )
    follow_up_question: Optional[str] = Field(
        default=..., description="Additional question to ask the user if needed."
    )
    message_to_user: Optional[str] = Field(
        ..., description="Any message to convey to the user."
    )
    
class QuestionLLMResponse(BaseModel):
    questionToAsk: str

def evaluate_atomic_criterion_with_llm(atomic_criterion: AtomicCriterion) -> Optional[LLMResponse]:
    """
    Interacts with the user to evaluate if they satisfy the given atomic criterion.
    Uses OpenAI's LLM with Pydantic structured outputs.

    Args:
        atomic_criterion (AtomicCriterion): The criterion to evaluate.

    Returns:
        Optional[LLMResponse]: The final evaluation result.
    """
    logger.info("Evaluating atomic criterion using LLM.")
    conversation_history = [
        {
            "role": "system",
            "content": (
                "You are assisting in determining whether a user satisfies a specific clinical trial criterion. "
                "Ask the user any necessary questions to make the determination. "
                "Your responses should be in the specified JSON format."
            ),
        },
        {
            "role": "assistant",
            "content": (
                f"Please answer the following questions to determine if you meet this criterion: {atomic_criterion.raw_text}"
            ),
        },
    ]

    while True:
        # make llm call to come up with question
        question = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=conversation_history,
            temperature=0.0,
            response_format=QuestionLLMResponse,
        ).choices[0].message.parsed.questionToAsk
        
        print(question)

        # Get the user's response
        user_response = input("Your response: ").strip()
        conversation_history.append({"role": "user", "content": user_response})

        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=conversation_history,
                temperature=0.0,
                response_format=LLMResponse,
            )
            message = completion.choices[0].message

            if message.parsed:
                llm_response = message.parsed
                logger.debug("LLM Response: %s", llm_response.json())

                if llm_response.continueAsking:
                    # Add assistant's follow-up question to the conversation
                    conversation_history.append({
                        "role": "assistant",
                        "content": llm_response.follow_up_question
                    })
                    continue  # Continue the loop to ask the follow-up question

                # Final determination made
                return llm_response
            else:
                logger.warning("LLM failed to parse the response.")
                print("An error occurred. Please try again.")
                return None
        except Exception as e:
            logger.error("Error during evaluation: %s", e)
            print("An error occurred. Please try again.")
            return None