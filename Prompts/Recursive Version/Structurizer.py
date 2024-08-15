import json
import rich

from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


# General criterion structure

class Category(str, Enum):
    # NOTE: not a proper docstring but instead meant to be a description for the Enum to go in the schema when used for the llm call
    """ATOMIC: A criterion that cannot be broken down further
    HIERARCHICAL: A criterion that has other criterions which are dependent on it and add additional modifications in a hierarchical manner.
    COMPOUND: Two or more independent criterions that may be joined by logical operators either 'AND' or 'OR' implicitly or explicitly"""
    ATOMIC_CRITERION = "atomic_Criterion"
    HIERARCHICAL_CRITERION = "hierarchical_criterion"
    COMPOUND_CRITERION = "compound_Criterion"

class Criterion(BaseModel):
    raw_text: str

class CategorizedCriterion(Criterion):
    category: Category


# Below identifies a criterion's category

class IndividualAnalysis(BaseModel):
    category: Category = Field(..., description="Category you are currently assessing")
    thoughts: str = Field(..., description="Your thoughts on if it classifies as this category")
    decision: bool = Field(..., description="Your decision on whether it classifies as this category")

class CategorizingStructure(BaseModel):
    individual_analyses: List[IndividualAnalysis]
    overall_thoughts: str
    final_category: Category

def categorize_Criterion(criterion: Criterion, verbose = False) -> CategorizedCriterion | None:
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": "You are an expert in categorizing clinical trial eligibility criteria in a hierarchical manner. Your task is to classify the top-level category of a given criterion. This means you must identify the highest level category that encompasses all subcategories",
            },
            {"role": "user", "content": criterion.raw_text},
        ],
        response_format=CategorizingStructure,
    )

    message = completion.choices[0].message
    if message.parsed:
        if verbose:
            print("Input: ", criterion, end="\n\n")
            rich.print(message.parsed)
        return CategorizedCriterion(raw_text=criterion.raw_text, category=message.parsed.final_category)
    else:
        if verbose:
            print(message.refusal)
        return None


# Below turns a generic criterion into an atomic criterion
class Target(BaseModel):
    answer: str = Field(..., description="An answer that would be considered true in regards to the Term")
    dependent_criterion: Optional[Criterion] = Field(...,description="Additional criteria which apply only if this answer is true")

class CollateralVariable(BaseModel):
    term: str = Field(..., description="A term which you must learn more about in order to determine the answer for the main term")
    information_gain: list[str] = Field(..., description="What we learned about said term")

class AtomicCriterion(CategorizedCriterion):
    root_term: str = Field(..., description="The root term of the criterion, as isolated as possible without any qualifiers or additional information")
    qualifiers: List[str] = Field(..., description="Qualifiers that may be used to further specify the criterion")
    relation_type: str = Field(..., description="The type of relationship between the root_term and the target")
    # possibly make the relation type restricted to more easily parse for eventual EHR integration 
    target: List[Target] = Field(..., description="A list of targets for which [root_term] [relation_type] [target] would mark the criterion as true")
    additional_information: List[str] = Field(..., description="Additional information from the raw text that provides context for the criterion but is not necessary to determine if the criterion is true. Must be quotes or loosely paraphrased for grammar purposes and to ensure the context is maintained")
    
    # TODO: implement optimization
    # possible optimization to reduce patient fatigue
    # extra_information: List[CollateralVariable] = Field(..., description="Additional information that may be needed to determine if the criterion is true")


class HierarchicalCriterion(CategorizedCriterion):
    parent_Criterion: Criterion = Field(..., description="The parent criterion that the child criterion is dependent on")
    child_Criterion: Criterion = Field(..., description="The additional modifications that the child criterion adds to the parent criterion")
    additional_information: List[str] = Field(..., description="Additional information from the raw text that provides context for the criterion but is not necessary to determine if the criterion is true. Must be quotes or loosely paraphrased for grammar purposes and to ensure the context is maintained")

class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"

class CompoundCriterion(CategorizedCriterion):
    logical_operator: LogicalOperator = Field(..., description="The logical operator that joins the two or more independent criterions")
    criterions: List[Criterion] = Field(..., description="The criterions that are joined by the logical operator")

def categorize_and_structurize(criterion: Criterion, verbose = False) -> AtomicCriterion | HierarchicalCriterion | CompoundCriterion | None:
    categorized_criterion = categorize_Criterion(criterion, verbose)
    if categorized_criterion is None:
        return None
    return structurize_once(categorized_criterion, verbose)

def structurize_once(criterion: CategorizedCriterion, verbose = False) -> AtomicCriterion | HierarchicalCriterion | CompoundCriterion | None:
    category_to_response_format = {
        Category.ATOMIC_CRITERION: AtomicCriterion,
        Category.HIERARCHICAL_CRITERION: HierarchicalCriterion,
        Category.COMPOUND_CRITERION: CompoundCriterion
    }
    if criterion.category == Category.ATOMIC_CRITERION:
        # TODO make it so qualifiers must all be true in order for the criterion to be true, for example in "caricnoid or neuroendocrine tumor" the terms "caricnoid" and "neuroendocrine tumor" are not qualifiers because its a one or the other
        # TODO that dependent criterion is uhhhh just not working right. below is an example
            # AtomicCriterion(
            # raw_text='Patients with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas)',
            # category=<Category.COMPOUND_CRITERION: 'compound_Criterion'>,
            # root_term='tumors',
            # qualifiers=['biopsy-proven', 'metastatic', 'carcinoid', 'neuroendocrine'],
            # relation_type='is',
            # target=[
            #     Target(answer='carcinoid', dependent_criterion=Criterion(raw_text='Patients with biopsy-proven metastatic carcinoid tumors')),
            #     Target(answer='Islet cell', dependent_criterion=Criterion(raw_text='Patients with biopsy-proven metastatic Islet cell tumors')),
            #     Target(answer='Gastrinoma', dependent_criterion=Criterion(raw_text='Patients with biopsy-proven metastatic Gastrinomas')),
            #     Target(answer='VIPoma', dependent_criterion=Criterion(raw_text='Patients with biopsy-proven metastatic VIPomas'))
            # ],
            # additional_information=['Patients must have either carcinoid tumors or other specified neuroendocrine tumors', 'Examples of other neuroendocrine tumors include Islet cell, Gastrinomas, and VIPomas.']  
        prompt = "You are an expert in parsing and interpreting atomic clinical trial eligibility criteria into its components. Your task is to identify the relationship triplet between the root term, the relationship, and the target. additionally you will identify any qualifiers that may be present"
    elif criterion.category == Category.HIERARCHICAL_CRITERION:
        prompt = "You are an expert in structurizing clinical trial eligibility criteria into hierarchical criterions. Your task is to break down a given criterion into its hierarchical components"
    elif criterion.category == Category.COMPOUND_CRITERION:
        # TODO: watch out for the word independent because they might take things such as caricnoid or neuroendocrine tumor as one criterion since there aren't two "independent" criterions
        prompt = "You are an expert in structurizing clinical trial eligibility criteria into compound criterions. Your task is to break down a given criterion into its compound components"
    else:
        return None


    completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {"role": "user", "content": criterion.raw_text},
            ],
            response_format=category_to_response_format[criterion.category],
        )

    if response := completion.choices[0].message.parsed:
        if verbose:
            print("Input: ", criterion.raw_text, end="\n\n")
            rich.print(response)
        return response
    else:
        return None

def structurize_fully(criterion: Criterion, verbose=False) -> AtomicCriterion | HierarchicalCriterion | CompoundCriterion | None:
    structured_criterion = categorize_and_structurize(criterion, verbose)
    if structured_criterion is None:
        return None
    if isinstance(structured_criterion, AtomicCriterion):
        return structured_criterion
    if isinstance(structured_criterion, HierarchicalCriterion):
        parent_criterion = structurize_fully(structured_criterion.parent_Criterion, verbose)
        child_criterion = structurize_fully(structured_criterion.child_Criterion, verbose)
        
        if parent_criterion is None or child_criterion is None:
            return None
        
        return HierarchicalCriterion(
            raw_text=criterion.raw_text,
            category=structured_criterion.category,
            parent_Criterion=parent_criterion,
            child_Criterion=child_criterion,
            additional_information=structured_criterion.additional_information
        )
    
    if isinstance(structured_criterion, CompoundCriterion):
        sub_criterions = []
        for c in structured_criterion.criterions:
            structured_c = structurize_fully(c, verbose)
            if structured_c is None:
                return None
            sub_criterions.append(structured_c)
        return CompoundCriterion(
            raw_text=criterion.raw_text,
            category=structured_criterion.category,
            logical_operator=structured_criterion.logical_operator,
            criterions=sub_criterions
        )

    return None

def main():
    atomic_example = "Patients with biopsy-proven metastatic neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas)"
    hierarchical_example = "Patients with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas) with at least one measurable lesion (other than bone) that has either not been previously irradiated or if previously irradiated has demonstrated progression since the radiation therapy."
    
    compound_example = "Patients, ages 18-65, with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas) with at least one measurable lesion (other than bone) that has either not been previously irradiated or if previously irradiated has demonstrated progression since the radiation therapy."
    
    criterion = Criterion(raw_text=hierarchical_example)
    structured_criterion = structurize_fully(criterion, verbose=True)
    assert structured_criterion is not None
    rich.print(structured_criterion)
    print(json.loads(structured_criterion.model_dump_json(indent=4)))

if __name__ == "__main__":
    main()