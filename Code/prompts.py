class BackgroundPrompt:
    def __init__(self, systemMessage, examples=None):
        self.systemMessage = systemMessage
        self.examples = examples
        self.messages = [
            {
                "role": "system",
                "content": self.systemMessage
            }
        ]
        if examples is None:
            return
        for example in examples:
            self.messages.append({
                "role": "user",
                "name": "example_user",
                "content": example[0]
            })
            self.messages.append({
                "role": "assistant",
                "name": "example_assistant",
                "content": example[1]
            })


textToBoolSystemMessage = """Context:
You will be provided text detailing eligibility criteria for a cancer research clinical trial. The text will typically consist of sections named "Inclusion Criteria" and "Exclusion Criteria". If a section's name isn't specified, treat it as "Inclusion Criteria" by default.

Task:
you will be converting plain text into a boolean algebra representation. this plain text may have ands, ors, buts, and other modifiers. Words like ineligible indicate that it should be in the exclusion criteria. This means that there are multiple conditions in one sentence. seperate them out and use operators. there should only be one condition per pair of {} brackets. input sentences may not have any operator between individual criteria, if that is the case you are to infer based on the following rules:

Inclusion Criteria: Combine all criteria using the "$and" operator.
Example: If criteria are A.B.C format them as:
"$and" : [{A},{B},{C}]

Exclusion Criteria: Use the "$or" operator between criteria and encompass the entire set with the "$not" operator.
Example: If the criteria are A.B.C format them as:
"$not":{"$or":[{A}{B}{C}]}

After formatting both sets, combine them with the "$and" operator.

Ensure that no individual term has an operator within it. Instead seperate into two terms surrounded with an operator. For Example:
AVOID: {"Liver or Lung Cancer}
PREFER:"$or"[
{"Liver Cancer"},
{"Lung Cancer"}
]

Some text may say canot participate if they have condition A, unless/until they have condition B. In this case it is part of the exclusion criteria, you will format it inside the exclusion not section as:
"$and" : [
{"A"},
{"$not":{"B"}}
]

Ensure all opened brackets, whether square [] or curly {}, are properly closed. Nested conditions might be present, you may nest as far as needed; 

Output:
Your output should strictly adhere to the provided format. Represent ANDs and ORs with [], while NOTs use {}. The goal is to output this structured Boolean algebra representation. Do not output anything else besides the boolean algebra representation. The following is an example input and what a valid output would look like:\n
"""
textToBoolExample = ("""Inclusion Criteria:\n\n• Patients with pathologically confirmed pancreatic cancer referred for image guided radiation therapy (IGRT)\n*White or Asian\n\nExclusion Criteria:\n\n* Age \\<18\n* Inability to consent\n* Known coagulopathy/thrombocytopenia (INR \\>1.5, platelets \\<75)\n* Patients on antiplatelet/anticoagulant medication that cannot safely be discontinued 5-7 days prior to the procedure\n* Gold allergy\n* Current infection\n*EUS evidence of vessel interfering with path of fiducial marker\n* Pregnancy""",
                     """{
    "$and":[
        {
            "$and": [
                {
                    "$and": [
                        {"pathologically confirmed pancreatic cancer"},
                        {"referred for image guided radiation therapy (IGRT)"}
                    ]
                },
                {
                    "$or": [
                        {"white race"},
                        {"asian race"}
                    ]
                }
            ]
        },
        {
            "$not": {
                "$or": [
                    {"less than 18 years old"},
                    {"Unable to consent"},
                    {"has Known coagulopathy/thrombocytopenia"},
                    {
                        "$and":[
                            {"is on antiplatelet/anticoagulant medication"},
                            {"cannot get off antiplatelet/anticoagulant medication 5-7 days prior to procedure"}
                        ]
                    },
                    {"has gold allergy"},
                    {"has current infection"},
                    {"has EUS evidence of vessel interfering with path of fiducial marker"},
                    {"is pregnant"}
                ]
            }
        }
    ]
}""")
booleanPrompt = BackgroundPrompt(systemMessage=textToBoolSystemMessage,
                                 examples=[textToBoolExample])

boolToMQLSystemMessage = """Context:You will be given a boolean algebra representation of criteria to participate in a clinical trial. While the Boolean algebra representation uses logical operators like "$and", "$or", and "$not", which are consistent with MQL, the internal key-value pairs do not follow MQL's conventions. Your job is to ensure that both the operators and their internal content align with MQL standards.

Guidelines:

Use MQL logical operators ["$and", "$or", "$not"]. They represent the relationship between individual criteria.

For number-based criteria, use numerical equality operators ["$eq", "$ne", "$gt", "$gte", "$lt", "$lte"]

For categorical-based criteria, use categorical equality operators ["$in", "$nin"]

Ensure a single condition for each segment.

Avoid making assumptions; translate only the given text.

Be concise when possible without removing clarity.

The entire thing must be surrounded in curly brackets {}. This is critical for it to be valid MQL

If the property can be read standalone, then make it a true or false statement.

in the case of a range of numbers, use both a "$gt" and an "$lt"

Additional Requirements:

In cases where numbers are presented in roman numerals, convert them to the Arabic number system. For example:
AVOID: "cancer stage" : {"$lte": III}
PREFER: "cancer stage":{"$lte":3}

In cases where numbers are presented in word form (e.g., 'eighteen' instead of '18'), convert them to their numeric counterparts.
AVOID: "ECOG status" : {"$gt" : "four"}
PREFER: "ECOG status" : {"$gt": 4}

Always place numbers in the value, not the property. for example:
AVOID: "age greater than 18": true
PREFER: "age": {"$gt": 18}

Prefer numbers over descriptive words whenever possible. Child means under 18 years, Adult means between 18 and 65, Senior means over 65. For example:
AVOID: "age" : "Adult"
PREFER: "age": {"$gt": 18, "$lt": 65}.

All timeframes, whether they are in weeks, months, years, or days, should be translated into a representation in days. 1 week = 7 days. 1 month is approximately 30 days. 1 year = 365 days. For example:
AVOID: "weeks since last chemotherapy": {"$lt": 3}
PREFER: "days since last chemotherapy": {"$lt": 21}

Do not output a mathematical expression; instead,  compute the expression. For example:
AVOID: "days since last radiation": {"$lt": 4 * 30}
PREFER:"days since last radiation":{"$lt":120}

When a criterion relates to the timeframe a patient has been off a medication or treatment, use a numerical representation to indicate the number of days since the last time they received that medication or treatment. Remember to represent timeframes in days. For example:
AVOID: "has had immunotherapy of any kind within the last 2 years": true
PREFER: "days since last immunotherapy": {"$gt": 730}

Don't use "$exists", instead, represent conditions as booleans. For example:
AVOID: "prior systematic therapy" : {"$exists" : true}
PREFER: "has prior systematic therapy": true

Prefer categories over booleans when possible.
AVOID: "has lung cancer": true
PREFER: "cancer type": "lung cancer"

Do not capitalize anything unless it is an acronym or a specific term/medicine. for example
AVOID: "Able to consent"
PREFER: "able to consent"

Make conditions specific, for example:
AVOID:"stage"
PREFER:"Cancer Stage"

Task:
Convert the provided Boolean algebra representation into a valid MongoDB query. Once done, ensure it adheres strictly to MQL standards and output only the finished MongoDB query.

Format:
Every MongoDB operator and condition must be surrounded by double quotes.
All brackets (both [] and {}) must be appropriately paired and closed.
Your response MUST adhere to JSOM and MQL formatting standards. Only output the MQL query, nothing else. NEVER break character."""
boolToMQLExample = ("""{
    "$and":[
        {
            "$and": [
                {
                    "$and": [
                        {"pathologically confirmed pancreatic cancer"},
                        {"referred for image guided radiation therapy (IGRT)"}
                    ]
                },
                {
                    "$or": [
                        {"white race"},
                        {"asian race"}
                    ]
                }
            ]
        },
        {
            "$not": {
                "$or": [
                    {"less than 18 years old"},
                    {"Unable to consent"},
                    {"has Known coagulopathy/thrombocytopenia"},
                    {
                        "$and":[
                            {"is on antiplatelet/anticoagulant medication"},
                            {"cannot get off antiplatelet/anticoagulant medication 5-7 days prior to procedure"}
                        ]
                    },
                    {"has gold allergy"},
                    {"has current infection"},
                    {"has EUS evidence of vessel interfering with path of fiducial marker"},
                    {"is pregnant"}
                ]
            }
        }
    ]
}""", """{
"and": [
{
"$or": [
{"race": "black"},
{"race": "white"}
]
},
{"ethnicity": {"$ne": "hispanic"}
},
{
"$and": [
{"age": {"$gte": 19,"$lte": 65}
},
{"able to travel daily": true}
]
},
{
"$not": {
"$or": [
{"has gastrointestinal (GI) conditions": true},
{"number of days since taken antibiotics or probiotics": {"$lt": 90}
},
{"smokes/uses tobacco": true},
{"consumes heavy alcohol": true},
{"has major medical conditions": true}
]
}
}
]
}
""")
MQLPrompt = BackgroundPrompt(systemMessage=boolToMQLSystemMessage,
                             examples=[boolToMQLExample])

fixJSONSystemMessage = """Context:
You will be provided with a MongoDB query written in Mongo DB Query Language (MQL), which is structured in JSON format. Your role is to validate the format and ensure it adheres strictly to the JSON formatting rules.

Guidelines:

Every key and string value in JSON must be enclosed in double quotes.
Objects are enclosed in curly braces {}.
Arrays are enclosed in square brackets [].
Key-value pairs within objects are separated by commas.
Values in arrays are separated by commas.
Ensure there are no trailing commas at the end of objects or arrays.
Ensure that all opened brackets (either { or [) are appropriately paired and closed with } or ] respectively.
Ensure there are no unnecessary or misplaced characters that don't belong to standard JSON format.
Numbers, true, false, and null are the only non-string values that don't require quotes.
Examples of Common Mistakes and Corrections:

Mistake: 'key': "value"
Correction: "key": "value" (Use double quotes for keys)

Mistake: "key": value
Correction: "key": "value" (String values must be in double quotes)

Mistake: "array": [value1, value2,]
Correction: "array": [value1, value2] (Remove trailing comma)

Mistake: { "key": "value" "anotherKey": "anotherValue" }
Correction: { "key": "value", "anotherKey": "anotherValue" } (Separate key-value pairs with commas)

Mistake: "key": [value1 value2]
Correction: "key": [value1, value2] (Separate array values with commas)

Mistake: { "key": "value"
Correction: { "key": "value" } (Close opened curly brace)

Task:
Review the provided MQL in JSON format. If it adheres to the JSON format without any errors simply re ouptut the input without any changes. If there are issues, correct them and provide the fixed version. In both cases you will only provide a correct MQL adhering to the JSON format.

Input:
"""


fixJSONPrompt = BackgroundPrompt(systemMessage=fixJSONSystemMessage)

# textHomogenizerTemplate = """Your role is to homogenize text. You will have a text and a list. your job is to modify the text to use the same modal expressions and terms as the list. You will replace words in the text with with their corresponding modal expressions and  terms in the list IF THEY HAVE THE SAME MEANING AND IT WON'T CHANGE THE MEANING OF THE TEXT. Do not change a word if it will change the meaning of the text. You will return the modified text. You will not change the text in any other way other than replacing modal expressions and terms with their corresponding pairs from the list. You will ONLY replace modal expressions and terms in the text and add Any important modal expressions and terms that were not altered to the list. DO NOT include any numbers in the list. The items in the list will be seperated via commas. Never return the list as "N/A", instead make the list based on the text. In either case, You will return two things: the modified text, and the updated list of words/phrases"""
