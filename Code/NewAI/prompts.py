class SystemPrompt:
    def __init__(self, systemMessage: str | None = None, examples=None):
        self.systemMessage = systemMessage
        self.messages = []
        if self.systemMessage is not None:
            if examples is not None:
                self.systemMessage += "\n\nExamples:\n"
                for example in examples:
                    self.systemMessage += "Example User:\n" + \
                        example[0] + "\n" + "Example Assistant:\n" + \
                        example[1] + "\n\n"
                self.systemMessage += "\nUser:\n"
            self.messages = [
                {
                    "role": "system",
                    "content": self.systemMessage
                }
            ]

        # for example in examples:
        #     self.messages.append({
        #         "role": "user",
        #         "name": "example_user",
        #         "content": example[0]
        #     })
        #     self.messages.append({
        #         "role": "assistant",
        #         "name": "example_assistant",
        #         "content": example[1]
        #     })

    def getSytemPrompt(self):
        return self.messages


class prepPrompts:
    @staticmethod
    def getChangeToNumericalPromp():
        message = "You will do one thing and one thing only. Should a numerical value be represented in anything except for a numerical value (for example: roman numeral, number word, etc.) you will swap it out with its numerical value. You will only change non numerical representations of numbers to their corresponding numerical value. Do not do anything else. You will only output the modified text, nothinng more. The following are all examples of how example inputs should be altered"
        examples = [
            ["i have one apple", "i have 1 apple"],
            ["i have three apples", "i have 3 apples"],
            ["i have nine apples", "i have 9 apples"],
            ["i have ten apples", "i have 10 apples"],
            ["i have eleven apples", "i have 11 apples"],
            ["i have twelve apples", "i have 12 apples"],
            ["i have thirteen apples", "i have 13 apples"],
            ["i have twenty apples", "i have 20 apples"],
            ["i have thirty apples", "i have 30 apples"],
            ["i have one hundred apples", "i have 100 apples"],
            ["i have one hundred and one apples", "i have 101 apples"],
            ["i have one hundred and ten apples", "i have 110 apples"],
            ["i have one hundred and eleven apples", "i have 111 apples"],
            ["i have one hundred and twenty apples", "i have 120 apples"],
            ["i have one hundred and twenty one apples", "i have 121 apples"],
            ["i have one hundred and thirty apples", "i have 130 apples"],
            ["stage i", "stage 1"],
            ["stage ii", "stage 2"],
            ["stage iii", "stage 3"],
            ["stage iv", "stage 4"],
            ["stage v", "stage 5"]]
        return SystemPrompt(systemMessage=message, examples=examples)
