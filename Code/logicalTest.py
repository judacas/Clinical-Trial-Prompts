import json
from models.logical_criteria import LogicalWrapperResponse
from models.identified_criteria import *
from utils.openai_client import get_openai_client
import logging
from typing import Union

logger = logging.getLogger()

client = get_openai_client()

sample_line = IdentifiedLine(
    line="Tissue from tumor must be available or if patient is over 18 years old, must have either a performance status of 0-1 or no prior chemotherapy but not both",
    criterions=[
        SingleRawCriterion(exact_snippets=["Tissue from tumor must be available"], criterion="tumor tissue", requirement_type="availability", expected_value=True),
        SingleRawCriterion(exact_snippets=["patient must be over 18 years old"], criterion="age", requirement_type="N/A", expected_value=NumericalComparison(operator = Operator.GREATER_THAN, value = 18)),
        SingleRawCriterion(exact_snippets=["performance status of 0-1"], criterion="performance status", requirement_type="range", expected_value=Range(comparisons=[NumericalComparison(operator = Operator.GREATER_THAN_OR_EQUAL_TO, value = 0), NumericalComparison(operator = Operator.LESS_THAN_OR_EQUAL_TO, value = 1)])),
        SingleRawCriterion(exact_snippets=["no prior chemotherapy"], criterion="prior treatment", requirement_type="presence", expected_value=False)
    ]
)

print(json.dumps(sample_line.model_dump(), indent=4))




prompt = (
    "You are an expert in clinical trial eligibility criteria."
    "Given the following line from an Oncological Clinical Trial Eligibility Criteria and its individual criteria, structure the criteria into logical relationships."
    
)

try:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": str(sample_line)},
        ],
        temperature=0.0,
        response_format=LogicalWrapperResponse,
    )
    if response := completion.choices[0].message.parsed:
        logger.debug("Successfully extracted atomic criteria from line: %s", sample_line)
        print(json.dumps(response.model_dump(), indent=4))
    else:
        logger.warning("Failed to parse LLM response.")
        print(completion.choices[0])
        raise ValueError(f"Failed to parse LLM response for line: '{sample_line}'")
except Exception as e:
    logger.error("Error during LLM extraction: %s", e)
    raise ValueError(f"Error during LLM extraction: {e}") from e


class LineType(Enum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    MISCELLANEOUS = "miscellaneous"