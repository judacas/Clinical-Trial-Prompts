# import json
import rich

from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional, Sequence
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
    COMPOUND_CRITERION = "compound_Criterion"
    HIERARCHICAL_CRITERION = "hierarchical_criterion"

class Criterion(BaseModel):
    raw_text: str

class CategorizedCriterion(Criterion):
    category: Category
    category_reasoning: str = Field(..., description="The reasoning behind why the criterion was classified as this category")
    overall_thoughts: str = Field(..., description="Categorizer's overall thoughts on the criterion")


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
        temperature=0.0,
        response_format=CategorizingStructure,
    )

    message = completion.choices[0].message
    if message.parsed:
        if verbose:
            print("Input: ", criterion, end="\n\n")
            rich.print(message.parsed)
        for categoryInfo in message.parsed.individual_analyses:
            if categoryInfo.category == message.parsed.final_category:
                return CategorizedCriterion(raw_text=criterion.raw_text, category=message.parsed.final_category, category_reasoning=categoryInfo.thoughts, overall_thoughts=message.parsed.overall_thoughts)
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
    root_term: str = Field(..., description="The root term of the criterion, as isolated as possible without any qualifiers or additional information. This is what you would ask the patient about to determine if the criterion is true")
    qualifiers: List[str] = Field(..., description="Qualifiers that may be used to further specify the criterion")
    relation_type: str = Field(..., description="The type of relationship between the root_term and the target, aka how you would structure the sentence to make it true. For example, 'has' or 'is' or 'has been diagnosed with' etc.")
    # possibly make the relation type restricted to more easily parse for eventual EHR integration 
    target: List[Target] = Field(..., description="A list of targets for which [root_term] [relation_type] [target] would mark the criterion as true")
    additional_information: List[str] = Field(..., description="Additional information from the raw text that provides context for the criterion but is not necessary to determine if the criterion is true. Must be quotes from the raw text and can not be a criterion on its won")
    
    # TODO: implement optimization
    # possible optimization to reduce patient fatigue
    # extra_information: List[CollateralVariable] = Field(..., description="Additional information that may be needed to determine if the criterion is true")


class HierarchicalCriterion(CategorizedCriterion):
    parent_Criterion: Criterion = Field(..., description="The parent criterion that the child criterion is dependent on")
    child_Criterion: Criterion = Field(..., description="The additional modifications that the child criterion adds to the parent criterion")
    additional_information: List[str] = Field(..., description="Additional information from the raw text that provides context for the criterion but is not necessary to determine if the criterion is true. Must be quotes from the raw text and can not be a criterion on its won")

class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"

class CompoundCriterion(CategorizedCriterion):
    logical_operator: LogicalOperator = Field(..., description="The logical operator that joins the two or more independent criterions")
    criterions: Sequence[Criterion] = Field(..., description="The criterions that are joined by the logical operator")

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
    prompt = "You are part of an nlp pipeline that is designed to structurize clinical trial eligibility criteria. You will be given a criterion by the user and your task is to parse the criterion into its components. You will be given context for why the criterion was classified as the category it was and you will be asked to parse the criterion into its components. You must use the text in your responses to ensure that the context is maintained and hallucination is avoided"
    prompt+="\n" + "You will be categorizing this as a"
    if criterion.category != Category.ATOMIC_CRITERION:
        prompt += f" {criterion.category}. "
    else:
        prompt += "n Atomic Criterion. "
    prompt += "Which means that "
    if criterion.category == Category.ATOMIC_CRITERION:
        # TODO make it so qualifiers must all be true in order for the criterion to be true, for example in "caricnoid or neuroendocrine tumor" the terms "caricnoid" and "neuroendocrine tumor" are not qualifiers because its a one or the other
        # TODO that dependent criterion is uhhhh just not working right.
        prompt = "the previous steps in the pipeline have brought it down to its smallest state where it is only one criterion. Your task is to identify the relationship triplet between the root term, the relationship, and the target. additionally you will identify any qualifiers that may be present"
    elif criterion.category == Category.HIERARCHICAL_CRITERION:
        prompt = "there is a parent criterion along with some child criterion which imposes further constraints on the parent criterion. Your task is to break down the given criterion into its hierarchical components."
        text_containers = "parent criterion and child criterion"
    elif criterion.category == Category.COMPOUND_CRITERION:
        # TODO: watch out for the word independent because they might take things such as caricnoid or neuroendocrine tumor as one criterion since there aren't two "independent" criterions
        prompt = "that this is really multiple criterions strung together with and And or and OR. you will find each of the individual criterions and parse them along with identifying the logical operator that joins them"
        text_containers = "independent criterions"
    else:
        return None
    
    if criterion.category != Category.ATOMIC_CRITERION:
        prompt+= "\n" + f"All of the raw text must be included in the {text_containers}. Should I find that your answer does not include all of the raw text, I will ask you to try again" # type: ignore has to be either hierarchical or compound so it will def be bound
    
    
    prompt += "\n\n" + f"Below is context for why the criterion was classified as {criterion.category}:\n\t{criterion.category_reasoning}\n\t{criterion.overall_thoughts}"
    prompt+= "\n\n" + "Now parse the criterion below into its components"


    completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user", 
                    "content": criterion.raw_text},
            ],
            response_format=category_to_response_format[criterion.category],
            temperature=0.0,
            
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
            additional_information=structured_criterion.additional_information,
            category_reasoning=structured_criterion.category_reasoning,
            overall_thoughts=structured_criterion.overall_thoughts
        )
    
    if isinstance(structured_criterion, CompoundCriterion):
        sub_criterions: Sequence[AtomicCriterion | HierarchicalCriterion | CompoundCriterion] = []
        for c in structured_criterion.criterions:
            structured_c: AtomicCriterion | HierarchicalCriterion | CompoundCriterion | None = structurize_fully(c, verbose)
            if structured_c is None:
                return None
            sub_criterions.append(structured_c)
        return CompoundCriterion(
            raw_text=criterion.raw_text,
            category=structured_criterion.category,
            logical_operator=structured_criterion.logical_operator,
            criterions=sub_criterions,
            category_reasoning=structured_criterion.category_reasoning,
            overall_thoughts=structured_criterion.overall_thoughts
        )

    return None

def main():
    examples = {
        "atomic_example": "Patients with biopsy-proven metastatic neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas)",
        
        "hierarchical_example": "Patients with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas) with at least one measurable lesion (other than bone) that has either not been previously irradiated or if previously irradiated has demonstrated progression since the radiation therapy.",
        
        "compound_example": "Patients, ages 18-65, with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas) with at least one measurable lesion (other than bone) that has either not been previously irradiated or if previously irradiated has demonstrated progression since the radiation therapy.",
        
        "simple_compound" : "Patients with stage 2 or 3 breast cancer and a history of smoking",
        "first__full_CHIA" : '''Patients with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas and VIPomas) with at least one measurable lesion (other than bone) that has either not been previously irradiated or if previously irradiated has demonstrated progression since the radiation therapy 
The patient has no major impairment of renal or hepatic function, as defined by the following laboratory parameters: total bilirubin <1.5 X ULN; AST, ALT<2.5X ULN (<5 X ULN if liver metastases are present) 
Patients on Sandostatin Lar (long acting somatostatin analogue) must be on a stable dose for 30 days prior to study entry and short acting somatostatin analogues must be judged to be on a clinically stable dose by the investigator prior to study entry 
Must have a life expectancy of greater than three (3) months 
Karnofsky Performance Status > 60 
Female patients must have a negative serum pregnancy test at screening. (Not applicable to patients with bilateral oophorectomy and/or hysterectomy or to those patients who are postmenopausal.) 
'''
    }
    
    example_key = "first__full_CHIA"
    criterion = Criterion(raw_text=examples[example_key])
    structured_criterion = structurize_fully(criterion, verbose=True)
    assert structured_criterion is not None
    json_data = structured_criterion.model_dump_json(indent=4, serialize_as_any=True) # in order for submodels to be fully serialized you need the serialize_as_any=True
    rich.print(structured_criterion)
    
    with open(f'structured_criterion_{example_key}.json', 'w') as file:
        file.write(json_data)

if __name__ == "__main__":
    main()