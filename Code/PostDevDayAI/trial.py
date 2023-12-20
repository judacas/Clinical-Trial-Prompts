import json
import re
from sympy import symbols, And, Or, Not, Implies
from Assistant import getResponse, ttbID, getAssistantObj, run, waitForRun
class Trial:
    def __init__(self, rawJSON, verbose = False, runAllAtOnce = False):
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
        if verbose:
            print(f"converted {self.title} to sympy json")
        if verbose:
            print(f"converting{self.title} to sympy expression")
        self.symPyExpression = parse_json_to_sympy(json.loads(self.symPyJSON))
        if verbose:
            print(f"converted {self.title} to sympy expression")
            
    def __str__(self):
        return json.dumps(self.toJSON(), indent=4)
    
    def toJSON(self):
        return {
            "id": self.id,
            "title": self.title,
            "symPyJSON": self.symPyJSON,
            "symPyExpression": str(self.symPyExpression)
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
        
            