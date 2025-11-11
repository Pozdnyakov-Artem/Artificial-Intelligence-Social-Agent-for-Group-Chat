class SimpleAgent:
    def __init__(self):
        self.message_history=[]

    def take_message(self, user, message):
        new_message = {"user": user, "message": message}

        self.message_history.append(new_message)

        response = self.make_response(message)

        return response

    def make_response(self, message):
        text_lower = message.lower()

        vocabulary_of_markers = ["встретиться", "встреча", "собраться","встретимся"]

        if any([word in vocabulary_of_markers for word in text_lower.split()]):
            return "Кажется, вы планируете встречу. Нужна помощь с согласованием времени?"

        return None

def main():
    agent = SimpleAgent()
    print(agent.take_message("Артём", "Хочу встретиться"))


if __name__ == '__main__':
    main()

