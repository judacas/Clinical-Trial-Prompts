import json

from Assistant import getAssistantObj, getFunctionCall, getResponse, infoGatherID, run


class Patient:
    def __init__(self, name, startingFile=None):
        self.name = name

        if startingFile is None:
            self.data = {"identifier": {"name": name}, "data": {}}
        else:
            json.load(startingFile)

    def saveJSON(self):
        with open(f"{self.name}Data.json", "w") as f:
            json.dump(self.data, f, indent=4)

    def addData(self, data):
        self.data["data"].update(data)

    def getData(self):
        return self.data["data"]

    def getJSON(self):
        return json.dumps(self.data)

    def getName(self):
        return self.name

    def acquireInformation(self, informationToAcquire: dict):
        assistant = getAssistantObj(infoGatherID)

        currentRun = run(assistant=assistant, newMsg=json.dumps(informationToAcquire))
        while currentRun.status != "requires_action":
            messageToUser = getResponse(currentRun.thread_id)
            userInput = input("\n" + messageToUser + "\n\n")
            print("getting AI response")
            currentRun = run(
                assistant=assistant, thread=currentRun.thread_id, newMsg=userInput
            )
        # trunk-ignore(ruff/F841)
        toolCalls = getFunctionCall(currentRun.thread_id, currentRun.id)["tool_calls"]
        dataRecovered = json.loads(toolCalls[0]["function"]["arguments"])
        print(dataRecovered)
        self.addData(dataRecovered)
        self.saveJSON()
        
