from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

def getValidInput(question: str, valid_type: type = None, valid_answers: list = None):  # type: ignore
    # this is just xoring them so that only one of them can be given
    if valid_type is None != valid_answers is None:
        raise ValueError("You must provide exactly one of valid_type or valid_answers")

    while True:
        if valid_answers is not None:
            completer = WordCompleter(valid_answers, ignore_case=True)
            answer = prompt(question, completer=completer)
            for valid_answer in valid_answers:
                if answer.lower() == valid_answer.lower():
                    return valid_answer
            print(
                f"Invalid input. Please enter one of the following: {', '.join(valid_answers)}"
            )
        else:
            try:
                # Try to convert the input to the valid type
                answer = valid_type(prompt(question))
                return answer
            except ValueError:
                print(
                    f"Invalid input. Please enter a value of type {valid_type.__name__}."
                )

# Example usage:
valid_answers = ["apple", "banana", "orange", "ajhhhhhh", "ajhhj"]
print(getValidInput("Enter a fruit: ", valid_answers=valid_answers))