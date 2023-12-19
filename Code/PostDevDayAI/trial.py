import json
import re
from sympy import symbols, And, Or, Not, Implies, simplify
from Assistant import ttbPrompt, ttbID, runAndGetResponse, getAssistantObj, show_json
class Trial:
    def __init__(self, rawJSON, symPyJSON = None, symPyExpression= None, verbose = False):
        self.rawJSON = rawJSON
        self.id = rawJSON["identificationModule"]["nctId"]
        self.title = rawJSON["identificationModule"]["officialTitle"]
        if symPyJSON is None:
            assert ttbID is not None
            if verbose:
                print(f"converting{self.title} to sympy json")
            self.symPyJSON = runAndGetResponse(newMsg=rawJSON["eligibilityModule"], assistant=getAssistantObj(ttbID), verbose=True)
            self.symPyJSON = self.symPyJSON[self.symPyJSON.find("{"):self.symPyJSON.rfind("}")+1]
            if verbose:
                print(f"converted {self.title} to sympy json")
            
        else:
            self.symPyJSON = symPyJSON
        if symPyExpression is None:
            if verbose:
                print(f"converting{self.title} to sympy expression")
            self.symPyExpression = parse_json_to_sympy(json.loads(self.symPyJSON))
            if verbose:
                print(f"converted {self.title} to sympy expression")

        else:
            self.symPyExpression = symPyExpression
            
    def __str__(self):
        return json.dumps(self.toJSON(), indent=4)
    
    def toJSON(self):
        return {
            "id": self.id,
            "title": self.title,
            "symPyJSON": self.symPyJSON,
            "symPyExpression": self.symPyExpression
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
        
            