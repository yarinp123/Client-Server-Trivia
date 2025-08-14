import socket
import struct
import threading
import os
import sys

# Client details
SERVER_PORT = 13117
BUFFER_SIZE = 1024
NAME = ""
HEADER = 64
FORMAT = 'utf-8'
lock = threading.Lock
ConnectionFlag = True

def listen_for_offers():
    print("Looking for a server...")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind(('', SERVER_PORT))
        while True:
            data, (ip, _) = udp_socket.recvfrom(BUFFER_SIZE)
            cookie, message_type, server_tcp_port = struct.unpack('!IbH', data)
            if cookie == 0xabcddcba and message_type == 0x2:
                return ip, server_tcp_port

def connect_to_server(server_ip, server_port : int, name : str):
    """Function to connect to a server after reciving UDP offer """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.connect((server_ip, server_port))
            print(f"Connected to {server_ip}:{server_port}.")
            message = f"NP{name}\n"
            tcp_socket.sendall(message.encode(FORMAT))
            server_msg = tcp_socket.recv(BUFFER_SIZE).decode(FORMAT) #welcome from server
            if server_msg == "Join_Successfully":
                ConnectionFlag = True
    except socket.error as e:
        print(f"Socket error: {e} in connecting to server")
    except Exception as e:
        print(f"An unexpected error occurred: {e} in connecting to server")

def reciver_message_from_server(tcp_socket : socket.socket) -> str:
    """This Function Recives the data from the server
     and returns a decoded string to the user"""
    try:
        server_msg = tcp_socket.recv(BUFFER_SIZE).decode(FORMAT)
        if server_msg.startswith("Time to start :") or server_msg.startswith("True or False ? :"):
            return server_msg
        elif server_msg.startswith("Incorrect"):
            return ("Wrong answer exiting game...") #start leaving the game
        elif server_msg.startswith("Correct"):
            pass # continue Game
    except socket.error as se:
        print(f"Socket error: {se} in receiving data")
    except Exception as e:
        print(f"An unexpected error occurred: {e} in receiving data")

def send_message_to_server(tcp_socket:socket.socket, answer:str)->None:
    """This function recives the user input,
     converts it to a signal byte and sends to server with 1 byte
     \x00 - False
     \x01 - True
     \x02 - Joinging the server with name (10 char)
     \x03 - Looking for a game
     \x04  -Looking for player
     \x05 - quit game
     \x06 - Exit server
     """
    try:
        if len(answer)>20: # max sent bytes for client is 20
            raise ValueError("Message Too long for sending")
        else:
            if type(answer) == bool:
                if True:
                    tcp_socket.sendall(b'\x01') # send 1 in byte for Ture
                else: tcp_socket.sendall(b'\x00') # send 0 for False
            else:
                if isinstance(answer, str):
                    if answer!= 'quit' and answer != 'Exit':
                        encoded_data = answer.encode('utf-8')  # Encoding the text data to bytes
                        padded_data = encoded_data.ljust(10, b'\x00')  # Padding data to ensure it is exactly 10 bytes
                        tcp_socket.sendall(b'\x02' + padded_data)
                else:
                    msg = b'\x05' if quit else b'\x06'
                    tcp_socket.sendall(msg)
    except ValueError as e:
        print(f"[ERROR] : {e}")
    except socket.error as e:
        print(f"[ERROR] Network error : {e}")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

def connect_to_server0(server_ip, server_port : int, name : str):
    """Function to connect to a server after reciving UDP offer """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.connect((server_ip, server_port))
        print(f"Connected to {server_ip}:{server_port}.")
        message = f"NP{name}\n"
        tcp_socket.sendall(message.encode(FORMAT))
        server_msg = tcp_socket.recv(BUFFER_SIZE).decode(FORMAT) #welcome from server
        print(server_msg)
        if server_msg == "Join_Server_Successfully":
            try:
                tcp_socket.sendall("waiting".encode(FORMAT))
                os.system('cls')
                print("Welcome to Dumbeldor\'s order Trivai Game were we practice our general knowledge ")
                while True:
                    server_msg = tcp_socket.recv(BUFFER_SIZE).decode(FORMAT)
                    if server_msg.startswith("Time to start :"):
                        tcp_socket.sendall("waiting".encode(FORMAT))
                    elif server_msg.startswith("True or False ? :"):
                        msg = input(server_msg)
                        if msg.startswith("T") or msg.startswith("True"):
                            tcp_socket.sendall("True".encode(FORMAT))
                        elif msg.startswith("F") or msg.startswith("False"):
                            tcp_socket.sendall("False".encode(FORMAT))
                        else:
                            while msg.startswith("F") or msg.startswith("False") or msg.startswith(
                                    "T") or msg.startswith("True"):
                                print("Wrong input Can answer only with True/False statements")
                                msg = input("Answer with True,T,1 for True \n False,F,0 for False \n")
                    elif server_msg.startswith("Incorrect"):
                        print("Wrong answer exiting game...")
                    elif server_msg.startswith("Correct"):
                        tcp_socket.sendall("Correct".encode(FORMAT))
                    else:
                        print(server_msg)
                        tcp_socket.sendall("waiting".encode(FORMAT))

            except ValueError as ve:
                print(f"Error processing message: {ve}")
            except socket.error as se:
                print(f"Socket error: {se}")
            except Exception as e:
                print(f"An unexpected error occurred: {e} in processing response")
        else:
            if server_msg:
                print(f"Failed to join server : {server_msg}")


def main():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            name = input("Enter user name: (max 10 chars)")
            while len(name) > 10:
                name = input("please enter shorter name")
            os.system('cls') # clear the screen
            print(f"Welcome {name} to Dumbeldor\'s order Trivai Game were we practice our general knowledge ")
            server_ip, server_port = listen_for_offers()
            print(f"Received offer from {server_ip}, attempting to connect...")
            tcp_socket.connect((server_ip, server_port))
            print(f"Connected to {server_ip}:{server_port}.")
            if name:
                send_message_to_server(tcp_socket, name)
                response = reciver_message_from_server(tcp_socket)
                print(response)
                while ConnectionFlag:
                    response = reciver_message_from_server(tcp_socket)
                    print(response)
                    if response.startswith("True or False ? :"):
                        answer = input("")
                        if answer == "True":
                            send_message_to_server(tcp_socket,True)
                        if answer == 'Fales':
                            send_message_to_server(tcp_socket, False)
                        if answer == 'quit':
                            send_message_to_server(tcp_socket,'quit')
                        if answer == 'exit':
                            send_message_to_server(tcp_socket,answer)
                        else:
                            print("bad input")
    except socket.timeout:
        print("[ERROR] TimeOut error lost connection to server")



if __name__ == '__main__':
    main()
