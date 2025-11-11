import time

def simulate_chat():
    messages = [
        {"user": "Анна", "text": "Ребята, давайте встретимся на выходных!"},
        {"user": "Борис", "text": "Я за! Предлагаю сходить в кафе"},
        {"user": "Виктор", "text": "У меня суббота свободна"},
        {"user": "Анна", "text": "Я в субботу тоже могу"}
    ]

    for msg in messages:
        # print(f"[{msg['user']}: {msg['text']}]")
        # time.sleep(1)
        yield msg['user'], msg['text']

def main():
    chat_generator = simulate_chat()

    try:
        while True:
            user, message = next(chat_generator)

            print(f"Получено от {user}: {message}")
    except StopIteration:
        print("Все сообщения чата обработаны!!!")

if __name__ == '__main__':
    main()