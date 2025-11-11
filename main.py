import chat_simulator.chat_simulator as chat_simulator
import agent_core.agent_core as agent_core


def main():
    chat_generator = chat_simulator.simulate_chat()

    agent = agent_core.SimpleAgent()

    try:
        while True:
            user, message = next(chat_generator)
            answ = agent.take_message(user, message)
            print(f"Получено от {user}: {message}")

            if answ:
                print(answ)

    except StopIteration:
        print("Все сообщения чата обработаны!!!")

if __name__ == "__main__":
    main()