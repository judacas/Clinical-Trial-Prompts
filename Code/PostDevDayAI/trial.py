import json
import re
from sympy import symbols, And, Or, Not, Implies
import sympy
from Assistant import getResponse, ttbID, getAssistantObj, run, waitForRun
class Trial:
    def __init__(self, serializedJSON = None, rawJSON = None, verbose = False, runAllAtOnce = False):
        if serializedJSON is not None:
            if rawJSON is not None:
                raise ValueError("Cannot have both serializedJSON and rawJSON")
            self.id = serializedJSON["id"]
            self.title = serializedJSON["title"]
            self.symPyJSON = serializedJSON["symPyJSON"]
            if isinstance(self.symPyJSON, str):
                self.symPyJSON = json.loads(self.symPyJSON)
            # self.symPyExpression = parse_json_to_sympy(self.symPyJSON)
            self.symPyExpression = (serializedJSON)["symPyExpression"]
            self.symPyExpression = sympy.sympify(self.symPyExpression)
            return
        else:
            if rawJSON is None:
                raise ValueError("Must have either serializedJSON or rawJSON")
            self.rawJSON = rawJSON
            self.id = rawJSON["identificationModule"]["nctId"]
            self.title = rawJSON["identificationModule"]["officialTitle"]
            if verbose:
                print(f"converting: {self.title} to sympy json")
            # change later to verbose = verbose
            self.symPyJSONRun = run(assistant=getAssistantObj(ttbID), newMsg=rawJSON["eligibilityModule"], verbose=False, wait=False)
            if runAllAtOnce:
                self.finishTranslation(verbose=verbose)
    def finishTranslation(self, verbose = False):
        self.symPyJSONRun = waitForRun(self.symPyJSONRun)
        self.symPyJSON = getResponse(self.symPyJSONRun.thread_id)
        self.symPyJSON = self.symPyJSON[self.symPyJSON.find("{"):self.symPyJSON.rfind("}")+1]
        try:
            # Try to parse self.symPyJSON into a Python dictionary
            self.symPyJSON = json.loads(self.symPyJSON)
        except json.JSONDecodeError:
            # If parsing fails, set symPyJSON to an error message
            self.symPyJSON = "Invalid JSON"

        if verbose:
            print(f"converted {self.title} to sympy json")
            print(f"converting{self.title} to sympy expression")
        self.symPyExpression = parse_json_to_sympy(self.symPyJSON)
        if verbose:
            print(f"converted {self.title} to sympy expression")
            
    def __str__(self):
        return json.dumps(self.toJSON(), indent=4)
    
    def toJSON(self):
        return {
            "id": self.id,
            "title": self.title,
            "symPyJSON": self.symPyJSON,
            "symPyExpression": sympy.srepr(self.symPyExpression)
        }
        
            

def parse_json_to_sympy(json_obj):
    if json_obj['type'] == 'variable':
        variableName = re.sub(r'[\s,]', '_', json_obj['value'])
        return symbols(variableName)
    elif json_obj['type'] == 'and':
        return And(*[parse_json_to_sympy(op) for op in json_obj['operands']])
    elif json_obj['type'] == 'or':
        return Or(*[parse_json_to_sympy(op) for op in json_obj['operands']])
    elif json_obj['type'] == 'not':
        assert len(json_obj['operands']) == 1  # Not should only have one operand
        return Not(parse_json_to_sympy(json_obj['operands'][0]))
    elif json_obj['type'] == 'implies':
        assert len(json_obj['operands']) == 2  # Implies should have exactly two operands
        return Implies(parse_json_to_sympy(json_obj['operands'][0]), parse_json_to_sympy(json_obj['operands'][1]))
        
            