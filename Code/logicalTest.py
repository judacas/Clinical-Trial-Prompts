import rich
from main import ColoredFormatter
from services.logical_structurizer import CriteriaType, logically_structurize_line, logically_structurize_trial
from models.logical_criteria import LLMLogicalAnd, LogicalWrapperResponse
from models.identified_criteria import *
from utils.openai_client import get_openai_client
import logging
from repositories.trial_repository import load_pydantic_model, save_pydantic_model


formatter = ColoredFormatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=None, style="%"
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO, handlers=[handler]  # Set to DEBUG to capture debug messages
)
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


# structured_line = logically_structurize_line(sample_line, CriteriaType.MISCELLANEOUS)
# rich.print(structured_line)
sample_and = LLMLogicalAnd(and_criteria=[SingleRawCriterion(exact_snippets=["Tissue from tumor must be available"], criterion="tumor tissue", requirement_type="availability", expected_value=True), SingleRawCriterion(exact_snippets=["patient must be over 18 years old"], criterion="age", requirement_type="N/A", expected_value=NumericalComparison(operator = Operator.GREATER_THAN, value = 18)), LLMLogicalAnd(and_criteria=[SingleRawCriterion(exact_snippets=["performance status of 0-1"], criterion="performance status", requirement_type="range", expected_value=Range(comparisons=[NumericalComparison(operator = Operator.GREATER_THAN_OR_EQUAL_TO, value = 0), NumericalComparison(operator = Operator.LESS_THAN_OR_EQUAL_TO, value = 1)])), SingleRawCriterion(exact_snippets=["no prior chemotherapy"], criterion="prior treatment", requirement_type="presence", expected_value=False)])])
save_pydantic_model(sample_and, "test.json", "testing")

# if sample_trial := load_pydantic_model(
#     "output", "NCT00050349_newly_structured.json", IdentifiedTrial):
#     logger.info("Successfully loaded trial.")
#     logical_trial = logically_structurize_trial(sample_trial)
#     logger.info("Successfully structurized trial.")
#     rich.print(logical_trial)
#     save_pydantic_model(logical_trial, "structured_test_trial.json", "testing")