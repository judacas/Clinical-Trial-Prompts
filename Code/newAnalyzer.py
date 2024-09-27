import os
from Structurizer import CategorizedCriterion, HierarchicalCriterion, AtomicCriterion, CompoundCriterion, Category
from newTrial import RawTrialData, Trial
import instructor
from typing import Self, Any, Type, TypeVar, Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import rich
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

TRIALS_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "Trials")
CHIA_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "CHIA")

load_dotenv()
client = instructor.from_openai(OpenAI())

def checkAllForCancer(trials: list[RawTrialData]) -> list[bool]:
    return [checkForCancer(trial) for trial in trials]

class IsAboutCancer(BaseModel):
    is_about_cancer: bool

def checkForCancer(trial: RawTrialData) -> bool:
    if "Cancer" in trial.official_title:
        return True
    return client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        response_model=IsAboutCancer,
        messages=[
            {
                "role": "system",
                "content": "Does this trial involve cancer?",
            },
            {
                "role": "user",
                "content": trial.official_title,
            },
        ],
    ).is_about_cancer
    
def getNctIdsFromFolder(folder):
    try:
        return {str(file[:11]) for file in os.listdir(folder) if file.startswith("NCT")}
    except Exception as e:
        print(f"Error accessing folder {folder}: {e}")
        return set() 
    
def getTrialFolder():
    comparingCategory = getValidInput("Enter the category in which your trials are in", validAnswers=os.listdir(TRIALS_FOLDER), printOptions=True, keepTrying=True, verbose=True)
    comparingCategory = os.path.join(TRIALS_FOLDER, comparingCategory)
    comparingFolder = getValidInput("Enter the folder in which your trials are in", validAnswers=os.listdir(comparingCategory), printOptions=True, keepTrying=True, verbose=True)
    comparingFolder = os.path.join(comparingCategory, comparingFolder)
    return comparingFolder


def list_completer(text, state, valid_inputs):
    options = [str(x) for x in valid_inputs if str(x).startswith(text)]
    return options[state % len(options)]

def getRangeInput(min: float, max: float, isInt: bool = False) -> int | float:
    """inclusive exclusive and will keep on trying until the user gives a valid input"""
    while True:
        rawNum = input(f"Enter a {'integer' if isInt else 'number'} between {min} and {max}: ")
        try:
            num: int | float = int(rawNum) if isInt else float(rawNum)
        except ValueError:
            print(f"Invalid input. Please enter a {'integer' if isInt else 'number'}.")
            continue
        if min <= num <= max:
            return num

def getValidInput(question: str, validType: type = None, validAnswers: list[str] = None, printOptions=False, keepTrying=True, verbose=True):  # type: ignore
    if (validType is None) == (validAnswers is None):
        print("You must provide exactly one of valid_type or valid_answers")
        raise ValueError("You must provide exactly one of valid_type or valid_answers")

    def handleValidAnswers() -> str:
        completer = WordCompleter(list(validAnswers), ignore_case=True)
        question_with_options = f"{question} {validAnswers} - " if printOptions else f"{question} - "
        while True:
            answer = prompt(question_with_options, completer=completer)
            if answer.lower() in (valid_answer.lower() for valid_answer in validAnswers):
                return answer
            if verbose:
                print("Input was not one of the valid options.")
            if not keepTrying:
                return answer
            print("Please try again.")

    def handleValidType():
        while True:
            try:
                return validType(answer := prompt(question))
            except ValueError:
                print(f"Invalid input. Please enter a value of type {validType.__name__}.")
                if not keepTrying:
                    return answer # type: ignore

    return handleValidAnswers() if validAnswers is not None else handleValidType()




def savePydanticModel(model: BaseModel, folder: str, fileName: str) -> bool:
    try:
        # ! important to save with utf-8 encoding in order for it to not crash when writing things like '\u2265' (the greater than or equal to sign)
        with open(os.path.join(folder, fileName), 'w', encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=4))
    except Exception as e:
        print(f"Error saving model: {e}")
        return False
    return True

T = TypeVar('T', bound=BaseModel)

def getModelFromFolder(folder: str, model_class: type[T], file_name: str) -> Optional[T]:
    try:
        file_path = os.path.join(folder, file_name)
        with open(file_path, encoding="utf-8") as f:
            # rich.print(f.read())
            return model_class.model_validate_json(f.read())
    except FileNotFoundError:
        print(f"File not found for model ID {file_name}")
        return None
    except ValueError as e:
        print(f"Error Validating model {file_name}: {e}")
        return None

def ensureFolderHasRawTrials(folder: str):
    nctIds = getNctIdsFromFolder(folder)
    faultyIds = []
    for id in nctIds:
        
        trial = getModelFromFolder(folder, RawTrialData, f"{id}.json")
        if not trial:
            print(f"Could not read trial {id}")
            faultyIds.append(id)
    if not faultyIds:
        print("All trials are valid")
        return
        
    print(f"Folder {folder} has the following faulty trials: {faultyIds}")
    for id in faultyIds:
        try:
            trial = RawTrialData.fromOnlyNctID(id)
        except ValueError as e:
            print(f"Error reading trial {id}, simply can't save this one for some reason: {e}")
            continue
        if savePydanticModel(trial, folder, f"{id}.json"):
            print(f"Saved trial {id}")
            faultyIds.remove(id)
        else:
            print(f"Error saving trial {id}")
    if faultyIds:
        print(f"Folder {folder} still has the following faulty trials:")
        for id in faultyIds:
            print("\t",id)
    return faultyIds
        

def checkForCancerTest():
    print("where are your raw trials?")
    folder = getTrialFolder()
    nctIds = getNctIdsFromFolder(folder)
    print(nctIds)
    print("where would you like to save the cancer trials?")
    save_Folder = getTrialFolder()
    print("out of those the following are about cancer:")

    for id in nctIds:
        print(f"\nChecking {id}")
        try:
            trial: RawTrialData = RawTrialData.fromOnlyNctID(id)
        except ValueError as e:
            print(f"Error reading trial {id}: {e}")
            continue
        print(trial.official_title)
        is_cancer = checkForCancer(trial)
        print("Is about cancer" if is_cancer else "Is not about cancer")
        if is_cancer:
            try:
                with open(os.path.join(save_Folder, f"{trial.nct_id}.json"), 'w') as f:
                    f.write(trial.model_dump_json(indent=4))
            except Exception as e:
                print(f"Error saving trial {trial.nct_id}: {e}")

def checkAccuracy():
    folder = getTrialFolder()
    nctIds = getNctIdsFromFolder(folder)
    print(nctIds)
    print("where would you like to save your annotated trials?")
    save_Folder = getTrialFolder()
    
    for id in nctIds:
        print(f"\nChecking {id}")
        try:
            trial = getModelFromFolder(folder, RawTrialData, f"{id}.json")
        except Exception as e:
            print(f"Error reading trial {id}: {e}")
            continue
        rich.print(trial)
        print("now lets move through each decision and see if you agree with it")

class Approval(BaseModel):
    field_name: str
    field_value: Any
    approval: int = Field(..., ge=0, le=1)
    explanation: str
    
    @classmethod
    def approve(cls, field_name, field_value) -> Self:
        print("\nRelated to the field below")
        rich.print(field_name)
        rich.print(field_value)
        print("\n\nDo you approve of the above field?")
        approval = int(getRangeInput(min = 0, max = 1, isInt = False))
        explanation = input("Please explain why you gave that rating or leave blank if its just blatantly obvious: ")
        return cls(field_name = field_name, field_value = field_value, approval=approval, explanation=explanation)
        

# Step 3: Perform the Casting
def castToSpecificCriterion(obj: CategorizedCriterion, category: Category):
    category_to_class = {
            Category.HIERARCHICAL_CRITERION: HierarchicalCriterion,
            Category.COMPOUND_CRITERION: CompoundCriterion,
            Category.ATOMIC_CRITERION: AtomicCriterion
        }
    target_class: Type[CategorizedCriterion] = category_to_class[category]
    if not isinstance(obj, target_class):
        # Create a new instance of the target class and initialize it with the data from the original object
        new_obj = target_class(obj)
        return new_obj
    return obj

class ratedCriterion(CategorizedCriterion):
    approvals: list[Approval]

    @classmethod
    def from_unrated_criterion(cls, criterion: HierarchicalCriterion | CompoundCriterion | AtomicCriterion, approvals: list[Approval] | None = None) -> Self:
        # check if current criterion extends from basemodel then call it recursively, otherwise annotate
        if approvals:
            return cls(approvals=approvals, **criterion.model_dump())
        # approval_list = [
        #     Approval.approve(field, getattr(criterion, field))
        #     for field in criterion.model_fields.keys()
        # ]
        approval_list = []
        children = criterion.getChildren()
        print(type(criterion))
        rich.print(criterion)
        print(f"\n{len(children)} children")
        # we want mutability
        for i, child in enumerate(children):
            print(f"\n {i} out of {len(children)} is type {type(child)}")
            if not isinstance(child, CategorizedCriterion):
                continue
            children[i] = cls.from_unrated_criterion(child)

        return cls(approvals=approval_list, **criterion.model_dump())

def main():
    folder = getTrialFolder()
    # ensureFolderHasRawTrials(folder)
    nctIds = getNctIdsFromFolder(folder)
    # print(nctIds)
    for id in nctIds:
        print(f"\nChecking {id}")
        trial = getModelFromFolder(folder, Trial, f"{id}_NewlyStructurized.json")
        if not trial:
            print(f"Error reading trial {id}")
            continue
        # rich.print(trial)
        if not trial.structurized:
            print("Trial not structurized")
            continue
        
        annotated_trial = ratedCriterion.from_unrated_criterion(trial.structurized)
        rich.print(annotated_trial)
        savePydanticModel(annotated_trial, folder, f"{id}_Annotated.json")
        break
    # print("where would you like to save your annotated trials?")
    # save_Folder = getTrialFolder()
    
        
if __name__ == "__main__":
    main()
    
    
    
    # @classmethod
    # def from_unrated_atomic_criterion(cls, criterion: AtomicCriterion) -> Self:
    #     return cls(
    #         root_term_approval=Approval.approve(criterion.root_term),
    #         qualifiers_approval=Approval.approve(criterion.qualifiers),
    #         relation_type_approval=Approval.approve(criterion.relation_type),
    #         target_approval=Approval.approve(criterion.target),
    #         additional_information_approval=Approval.approve(criterion.additional_information),
    #         **criterion.model_dump()
    #     )
    

# def rateCategory(criterion: CategorizedCriterion) -> ratedCriterion:
#     print(criterion)
#     approval = int(getValidInput("Do you agree with the way that it is Categorized?", validType=int, validAnswers=[0,0.5,1]))
#     explanation = input("Please explain why you gave that rating: ")
#     return ratedCriterion(criterion=criterion, approval=approval, explanation=explanation)
    



# def rateAtomicCriterion(criterion: AtomicCriterion) -> ratedAtomicCriterion:
#     print(criterion)
#     int(getValidInput("Do you agree with the way that it is Categorized?", validType=int, validAnswers=[0,0.5,1]))
    
        
        


