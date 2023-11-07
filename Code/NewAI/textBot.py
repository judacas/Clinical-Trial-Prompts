import AI as Ai


def getValidInput():
    while True:
        text: str = input("Your input: ")
        if text != "":
            return text
        else:
            print("Please say something before pressing enter")


def main():
    ai = Ai.Ai()
    while True:
        user_input = getValidInput()
        ai.AskAI(user_input)
        ai.pretty_print_conversation()


if __name__ == "__main__":
    main()
