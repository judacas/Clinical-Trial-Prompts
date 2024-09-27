from pydantic import BaseModel, Field, create_model
from typing import Any, Optional, Type

import rich

# Base ApprovalMixin that contains the approval fields
class ApprovalMixin(BaseModel):
    rating: Optional[int] = Field(None, description="Rating for the field")
    explanation: Optional[str] = Field(None, description="Explanation for the rating")


# Function to dynamically create a new model with approval fields for each field in the original model
def create_approval_model(base_model: Type[BaseModel]) -> Type[BaseModel]:
    approval_fields:dict[Any,Any] = {
        f"{field_name}_approval": (ApprovalMixin, None)
        for field_name, field_info in base_model.model_fields.items()
    }
    # Dynamically create a new model with the added approval fields
    return create_model(
        f"Approval{base_model.__name__}",  # Model name
        __base__=base_model,  # Extend the original base model
        **approval_fields  # Dynamically added fields
    )

# Example original Pydantic model
class LLMResponseModel(BaseModel):
    name: str
    age: int
    is_student: bool
    someRecursiveNess: list["LLMResponseModel"]
    
    def getChildren(self):
        return self.someRecursiveNess
    
class childClass(LLMResponseModel):
    foo: str

# Create the approval version of the model
ApprovalLLMResponseModel = create_approval_model(LLMResponseModel)

sample_instance = LLMResponseModel(name="John Doe", age=22, is_student=True, someRecursiveNess=[childClass(name="Adam Smith", age=13, is_student=False, someRecursiveNess=[], foo="bar")])

rich.print(sample_instance)


# Example usage with both original fields and approval fields
sampleResponse = {
    "name": "John Doe",
    "age": 22,
    "is_student": True,
}

# Create an instance of the dynamically created approval model
# approval_instance = ApprovalLLMResponseModel(**data)
# rich.print(approval_instance)
