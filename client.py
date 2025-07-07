import socket


def main():
    host = '127.0.0.1'
    port = 8888
    buf_size = 1024
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    end = False
    while not end:
        message = client.recv(buf_size).decode()
        if message == 'end':
            end = True
            break
        need_response = message.split()[-1] == 'need_response'
        print(message)
        if need_response:
            message = input('>>> ')
            client.sendall(message.encode())
    client.close()


if __name__ == '__main__':
    main()
