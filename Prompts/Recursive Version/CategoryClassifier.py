import rich

from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

class Criterion_type(str, Enum):
    """ATOMIC: A criterion that cannot be broken down further
    HIERARCHICAL: A criterion that has other criterions which are dependent on it and add additional modifications in a hierarchical manner.
    COMPOUND: Two or more independent criterions that may be joined by logical operators either 'AND' or 'OR' implicitly or explicitly"""
    ATOMIC_CRITERION = "atomic_Criterion"
    HIERARCHICAL_CRITERION = "hierarchical_criterion"
    COMPOUND_CRITERION = "compound_Criterion"


class Analysis(BaseModel):
    category: Criterion_type = Field(..., description="Category you are currently assessing")
    thoughts: str = Field(..., description="Your thoughts on if it classifies as this category")
    decision: bool = Field(..., description="Your decision on whether it classifies as this category")

class Criterion_Classifier(BaseModel):
    individual_analyses: List[Analysis]
    overallThoughts: str
    final_category: Criterion_type

client = OpenAI()

criterion = "Patients with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas) with at least one measurable lesion (other than bone) that has either not been previously irradiated or if previously irradiated has demonstrated progression since the radiation therapy."

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {
            "role": "system",
            "content": "You are an expert in categorizing clinical trial eligibility criteria in a hierarchical manner. Your task is to classify the top-level category of a given criterion. This means you must identify the highest level category that encompasses all subcategories",
        },
        {"role": "user", "content": criterion},
    ],
    response_format=Criterion_Classifier,
)

message = completion.choices[0].message
if message.parsed:
    print("Input: ", criterion, end="\n\n")
    rich.print(message.parsed)

    # print("answer: ", message.parsed.final_category)
else:
    print(message.refusal)



