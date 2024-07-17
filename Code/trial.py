import json
import re
from typing import Any, Optional

import sympy
from Assistant import getAssistantObj, getResponse, run, ttbID, waitForRun
from errorManager import logError
from sympy import And, Implies, Not, Or, symbols


class Trial:
    # ! DO NOT USE RUNALLATONCE = FALSE
    # I'm pretty sure it used to work in parallel but now it doesn't, so for now just use runAllAtOnce = True and keep it serial
    # TODO: Fix runAllAtOnce so that it works in parallel
    def __init__(
        self, serializedJSON=None, rawJSON=None, verbose=False, runAllAtOnce=True
    ):
        if serializedJSON is not None:
            if rawJSON is not None:
                raise ValueError("Cannot have both serializedJSON and rawJSON")
            if isinstance(serializedJSON, str):
                try:
                    serializedJSON = json.loads(serializedJSON)
                except json.JSONDecodeError:
                    try:
                        with open(serializedJSON, "r") as file:
                            serializedJSON = json.load(file)
                    except FileNotFoundError as e:
                        raise ValueError(f"Could not find file {serializedJSON}") from e
            self.nctId = serializedJSON["nctId"]
            self.title = serializedJSON["title"]
            self.symPyJSON = serializedJSON["symPyJSON"]
            if isinstance(self.symPyJSON, str):
                try:
                    self.symPyJSON = json.loads(self.symPyJSON)
                except json.JSONDecodeError:
                    # If parsing fails, set symPyJSON to an error message
                    self.symPyJSON = (
                        "Invalid JSON. Below is the attempt at a json \n\n"
                        + self.symPyJSON
                    )
            # self.symPyExpression = parse_json_to_sympy(self.symPyJSON)
            try:
                self.symPyExpression = (serializedJSON)["symPyExpression"]
            except Exception as e:
                self.symPyExpression = "N/A"
                logError(e=e, during=f"converting {self.title} to sympy expression string")
            try:
                self.symPyExpression = sympy.sympify(self.symPyExpression)
            except Exception as e:
                self.symPyExpression = "N/A"
                logError(e=e, during=f"converting {self.title} to sympy expression")
            return
        else:
            if rawJSON is None:
                raise ValueError("Must have either serializedJSON or rawJSON")
            self.rawJSON = rawJSON
            self.nctId = rawJSON["nctId"]
            self.title = rawJSON["officialTitle"]
            if verbose:
                print(f"converting: {self.title} to sympy json")
            criteria_keys = ["inclusionCriteria", "exclusionCriteria", "Criteria"]
            criteria_dict = {
                key: rawJSON[key] for key in criteria_keys if key in rawJSON
            }
            self.symPyJSONRun = run(
                assistant=getAssistantObj(ttbID),
                newMsg=json.dumps(criteria_dict, indent=2),
                verbose=False,
                wait=False,
            )
            if runAllAtOnce:
                self.finishTranslation(verbose=verbose)

    def finishTranslation(self, verbose=False):
        self.symPyJSONRun = waitForRun(self.symPyJSONRun)
        self.symPyJSON = getResponse(self.symPyJSONRun.thread_id)
        self.symPyJSON = self.symPyJSON[
            self.symPyJSON.find("{") : self.symPyJSON.rfind("}") + 1
        ]
        try:
            # Try to parse self.symPyJSON into a Python dictionary
            self.symPyJSON = json.loads(self.symPyJSON)
        except json.JSONDecodeError:
            # If parsing fails, set symPyJSON to an error message
            self.symPyJSON = (
                "Invalid JSON. Below is the attempt at a json \n\n" + self.symPyJSON
            )

        if verbose:
            print(f"converted {self.title} to sympy json")
            print("\n\n")
            print(self.symPyJSON)
            print("\n\n")
            print(f"converting{self.title} to sympy expression")
        try:
            self.symPyExpression = parse_json_to_sympy(self.symPyJSON)
        except Exception as e:
            self.symPyExpression = "N/A"
            logError(e=e, during=f"converting {self.title} to sympy expression")
        if verbose:
            print(f"converted {self.title} to sympy expression")

    def __str__(self):
        return json.dumps(self.toJSON(), indent=4)

    def toJSON(self) -> dict[str, Any]:
        return {
            "nctId": self.nctId,
            "title": self.title,
            "symPyJSON": self.symPyJSON,
            "symPyExpression": sympy.srepr(self.symPyExpression),
        }

    def get_variables(self, json_obj: Optional[dict] = None):
        if json_obj is None:
            json_obj = self.symPyJSON  # type: ignore
        assert json_obj is not None
        # json_obj = self.toJSON()["sympyJSON"]
        # Initialize an empty list to store the variables
        variables = []

        # Check if the current object is a variable
        if json_obj["type"] == "variable":
            variables.append(json_obj["value"])
        # If the current object is an operator, recurse on its children
        else:
            for child in json_obj["operands"]:
                variables.extend(self.get_variables(child))
        return variables

    # ! This will probably crash eventually
    # TODO fix for when talking with trials
    # wait actually you can probably just make sure that symPyExpression is of type sympy.Expr
    # ! test this change, it used to be assert its not none
    def getVariableValue(self, variableName):
        assert isinstance(self.symPyExpression, sympy.Expr)
        variableName = re.sub(r"[\s,]", "_", variableName)
        for symbol in self.symPyExpression.free_symbols:
            # If the symbol's name matches the variable name, return the symbol
            if str(symbol) == variableName:
                return symbol
            # If the variable doesn't exist, return None
        return None

    # same issue as above getVariableValue
    def substituteMultipleVariables(self, variableValues: dict[str, bool]):
        assert isinstance(self.symPyExpression, sympy.Expr)
        self.symPyExpressionSolved = self.symPyExpression
        for variableName, variableValue in variableValues.items():
            variable = self.getVariableValue(variableName)
            if variable is None:
                # raise ValueError(f"Variable {variableName} does not exist")
                print(f"Variable {variableName} does not exist")
            self.symPyExpressionSolved = self.symPyExpressionSolved.subs(
                variable, variableValue
            )
        return self.symPyExpressionSolved


# def combineVariables(variables: list[list[str]]):
#     combinedVariables = []
#     for variable in variables:
#         combinedVariables.append(" and ".join(variable))
#     return " or ".join(combinedVariables)


def parse_json_to_sympy(json_obj):
    if json_obj["type"] == "variable":
        variableName = re.sub(r"\s", r"\\ ", json_obj["value"])
        variableName = re.sub(r",", r"\\,", variableName)
        variableName = re.sub(r":", r"\\:", variableName)
        return symbols(variableName)
    elif json_obj["type"] == "and":
        return And(*[parse_json_to_sympy(op) for op in json_obj["operands"]])
    elif json_obj["type"] == "or":
        return Or(*[parse_json_to_sympy(op) for op in json_obj["operands"]])
    elif json_obj["type"] == "not":
        assert len(json_obj["operands"]) == 1  # Not should only have one operand
        return Not(parse_json_to_sympy(json_obj["operands"][0]))
    elif json_obj["type"] == "implies":
        assert (
            len(json_obj["operands"]) == 2
        )  # Implies should have exactly two operands
        return Implies(
            parse_json_to_sympy(json_obj["operands"][0]),
            parse_json_to_sympy(json_obj["operands"][1]),
        )
