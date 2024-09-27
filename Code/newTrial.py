# Need to seperate structure from llm output, stuff like thoughts and categoryDecision are being output by the llm due to inheritance even though it was only supposed to be used as input.
# need to give an option to say its not a criterion and shouldn't be treated as one to avoid endless loops
# could also make another criterion type which says its a criterion but doesn't have enough context to structurize

import json
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat.parsed_chat_completion import ParsedChatCompletionMessage
from pydantic import BaseModel, BeforeValidator, Field, model_validator
import requests
import rich
from Structurizer import structurize_fully, CategorizedCriterion, Criterion
from typing import Annotated, Optional, Self

load_dotenv()
client = OpenAI()

class InclusionExclusionExtractionResponse(BaseModel):
    found: bool
    inclusion: Optional[str]
    exclusion: Optional[str]
    

def getIncAndExc(raw_text: str):    
    completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": "Identify the parts of the text that are the inclusion and/or exclusion criteria for a clinical trial. It should state it explicitly, if it doesn't then just set found to false",
                },
                {
                    "role": "user", 
                    "content": raw_text},
            ],
            response_format=InclusionExclusionExtractionResponse,
            temperature=0.0,
            
        )
    message: ParsedChatCompletionMessage[InclusionExclusionExtractionResponse] = completion.choices[0].message
    if message.parsed:
        return message.parsed
    else:
        return InclusionExclusionExtractionResponse(found=False, inclusion=None, exclusion=None)
        

class Criteria(BaseModel):
    raw_text: str
    inclusion: Optional[str] = None
    exclusion: Optional[str] = None

    @model_validator(mode='after')
    def set_inclusion_exclusion(self) -> Self:
        if not self.inclusion and not self.exclusion:
            inc_exc = getIncAndExc(self.raw_text)
            if inc_exc.found:
                self.inclusion = inc_exc.inclusion
                self.exclusion = inc_exc.exclusion
                
        return self

def checkStartsWithNCT(nct_id: str) -> str:
    if not nct_id.startswith("NCT"):
        raise ValueError(f"NCT ID {nct_id} must start with 'NCT'")
    return nct_id

def checkLength(nct_id: str) -> str:
    if len(nct_id) != 11:
        raise ValueError(f"NCT ID {nct_id} must be 11 characters long")
    return nct_id

NctIDValidated = Annotated[str, Field(alias='nct_id'), BeforeValidator(str.upper), BeforeValidator(checkStartsWithNCT), BeforeValidator(checkLength)]

def curlWithStatusCheck(url: str) -> dict:
    response: requests.Response = requests.get(url, timeout=10)
    if response.status_code != 200:
        print(f"Something Went wrong with a curl\n\n{response.text}")
        raise requests.exceptions.RequestException("Something Went Wrong with the ClinicalTrials API")

    return response.json()

class isCancerResponseFormat(BaseModel):
    is_cancer: bool
    keywords: list[str] = Field(..., description="exact keywords which signified if it was cancer, if is_cancer is false then this will be empty")
    
    @model_validator(mode='after')
    def checkKeywordsAgreesWithIsCancer(self) -> Self:
        if bool(self.is_cancer) != bool(self.keywords):
            raise ValueError("is_cancer and keywords must either be true and have keywords or be false and have no keywords")
        return self
    
    

class RawTrialData(BaseModel):
    nct_id: NctIDValidated
    official_title: str
    criteria: Criteria
    
    @classmethod
    def fromOnlyNctID(cls, nct_id: NctIDValidated) -> Self:
        raw_data = curlWithStatusCheck(
        f"https://clinicaltrials.gov/api/v2/studies?format=json&fields=EligibilityModule%7CNCTId%7COfficialTitle&query.cond={nct_id}"
            )
        try:
            official_title = raw_data["studies"][0]["protocolSection"]["identificationModule"]["officialTitle"]
            eligibilityModule = raw_data["studies"][0]["protocolSection"]["eligibilityModule"]
            criteriaText = eligibilityModule["eligibilityCriteria"]
        except KeyError as err:
            raise ValueError(f"Couldn't find the trial with ID {nct_id}") from err
        
        for extraCriteria in ["healthyVolunteers", "sex", "minimumAge", "maximumAge", "stdAges"]:
            if criteriaValue := eligibilityModule.pop(extraCriteria, None):
                criteriaText += f"\n\n{extraCriteria}: {criteriaValue}"
        
        criteria = Criteria(raw_text=criteriaText)
        return cls(nct_id=nct_id, official_title=official_title, criteria=criteria)
    
    
    # uncomment once I switch over to instructor because we have conflicting names
    # def checkForCancer(trial: RawTrialData) -> bool:
        # if "Cancer" in trial.official_title:
        #     return True
        # return client.chat.completions.create(
        #     model="gpt-4o-2024-08-06",
        #     response_model=IsAboutCancer,
        #     messages=[
        #         {
        #             "role": "system",
        #             "content": "Does this trial involve cancer?",
        #         },
        #         {
        #             "role": "user",
        #             "content": trial.official_title,
        #         },
        #     ],
        # ).is_about_cancer
        


class Trial(BaseModel):
    raw_data: RawTrialData
    structurized: Optional[CategorizedCriterion] = None
    
    @model_validator(mode='after')
    def structurize(self) -> Self:
        if not self.structurized:
            # TODO set up once it gets split into inc and exc
            # if self.raw_data.criteria.inclusion or self.raw_data.criteria.exclusion:
            #     if self.raw_data.criteria.inclusion and self.raw_data.criteria.exclusion:
            #         self.structurized = structurize_fully(criterion=Co(inclusion=self.raw_data.criteria.inclusion, exclusion=self.raw_data.criteria.exclusion))
            self.structurized = structurize_fully(criterion=Criterion(raw_text=self.raw_data.criteria.raw_text), verbose=True)
        return self
    
    
def main():
    trialIDs: list[str] = ["NCT00050349", "NCT00061308", "NCT00094861", "NCT00183885", "NCT00312429"]
    for id in trialIDs:
        trial = Trial(raw_data=RawTrialData.fromOnlyNctID(id))
        with open(f"{id}_NewlyStructurized.json", "w") as f:
            json.dump(trial.model_dump_json(serialize_as_any=True), f, indent=4)
        rich.print(trial)

if __name__ == "__main__":
    main()