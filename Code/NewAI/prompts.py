class SystemPrompt:
    def __init__(self, systemMessage=None, examples=None):
        self.systemMessage = systemMessage
        self.messages = []
        if systemMessage is not None:
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

    def getSytemPrompt(self):
        return self.messages
