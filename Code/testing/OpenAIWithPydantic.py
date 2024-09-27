from typing import Optional

import rich
from pydantic import BaseModel

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()


class optionalTest(BaseModel):
    someMessage: str
    optionalMessage: Optional[str]
    dontPutAnythingHere: Optional[str]


client = OpenAI()

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {
            "role": "system",
            "content": "just respond",
        },
    ],
    response_format=optionalTest,
)

message = completion.choices[0].message
rich.print(message.parsed)
