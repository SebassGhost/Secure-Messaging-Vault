from client.send import main as send_message
from client.receive import receive


def main():
    payload = send_message()
    receive(payload)


if __name__ == "__main__":
    main()
