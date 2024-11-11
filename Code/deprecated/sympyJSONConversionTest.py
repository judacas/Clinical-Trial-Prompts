import json
from sympy import symbols, And, Or, Not, Implies, simplify

def parse_json_to_sympy(json_obj):
    if json_obj['type'] == 'variable':
        return symbols(json_obj['value'])
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

# Example JSON object with Implies
json_expr = """
{
  "type": "implies",
  "operands": [
    {
      "type": "variable",
      "value": "A"
    },
    {
      "type": "and",
      "operands": [
        {
          "type": "variable",
          "value": "B"
        },
        {
          "type": "variable",
          "value": "C"
        },
        {
          "type": "not",
          "operands": [
            {
              "type": "variable",
              "value": "C"
            }
          ]
        }
      ]
    }
  ]
}
"""

json_expr = r"""
{
  "type": "and",
  "operands": [
    {
      "type": "and",
      "operands": [
        {
          "type": "variable",
          "value": "AgeBetween18And90ForEUSPancreasCystEvaluation"
        },
        {
          "type": "variable",
          "value": "MinimumAgeOf18Years"
        },
        {
          "type": "variable",
          "value": "MaximumAgeOf90Years"
        }
      ]
    },
    {
      "type": "not",
      "operands": [
        {
          "type": "or",
          "operands": [
            {
              "type": "variable",
              "value": "PatientOutsideAgeRange"
            },
            {
              "type": "variable",
              "value": "UnableToProvideConsent"
            },
            {
              "type": "variable",
              "value": "UnableToUnderstandEnglish"
            },
            {
              "type": "variable",
              "value": "AllergicToCipro"
            },
            {
              "type": "variable",
              "value": "HighRiskForInfectiveEndocarditis"
            },
            {
              "type": "variable",
              "value": "BacterialInfectionOrAntibioticsUseWithin6WeeksOfEUS"
            },
            {
              "type": "variable",
              "value": "PancreatitisWithinPast6Months"
            },
            {
              "type": "variable",
              "value": "UnderlyingImmunosuppression"
            },
            {
              "type": "variable",
              "value": "CurrentlyTakingImmunosuppressiveMedications"
            },
            {
              "type": "variable",
              "value": "CystCavityDebrisOrNecroticDebrisEvidence"
            },
            {
              "type": "variable",
              "value": "SevereSystemicDisease"
            }
          ]
        }
      ]
    }
  ]
}"""


# Parse the JSON object and create a SymPy expression
parsed_json = json.loads(json_expr)
sympy_expr = parse_json_to_sympy(parsed_json)

# Print the SymPy expression
print(f"SymPy Expression: {sympy_expr}")

# Simplify the expression
simplified_expr = simplify(sympy_expr)

# Print the simplified expression
print(f"Simplified Expression: {simplified_expr}")

# Get all variables used in the expression
variables = simplified_expr.free_symbols

# Print the variables
print(f"Variables in the expression: {variables}")

# Example: Substitute truth values
truth_values = {'A': True, 'B': True}
evaluated_expr = simplified_expr.subs(truth_values)

# Print the evaluated expression
print(f"Evaluated Expression: {evaluated_expr}")
