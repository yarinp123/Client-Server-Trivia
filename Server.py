import os
import socket
import threading
import struct
import random
import time

class Server:
    def __init__(self):
        self.games = TriviaGame()
        self.clients = {} #PORT:[Name,IP]
        self.lock = threading.Lock()
        self.SERVER_IP = socket.gethostbyname(socket.gethostname())
        self.SERVER_PORT = 13117
        self.TCP_PORT = 2112
        self.BUFFER_SIZE = 1024
        self.INPUT_BUFFER_SIZE = 12
        self.FORMAT = 'utf-8'
        self.shutdown_flag = threading.Event() #True means ongoing \ False means waiting for players

    def broadcast_offers(self):
        """Broadcasts offer messages to potential clients using UDP."""
        # Constants for UDP broadcasting
        MAGIC_COOKIE = 0xabcddcba
        MESSAGE_TYPE = 0x2
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            message = struct.pack('!IbH', MAGIC_COOKIE, MESSAGE_TYPE, self.TCP_PORT)
            while not self.shutdown_flag.is_set():
                try:
                    udp_socket.sendto(message, ('<broadcast>', self.SERVER_PORT))
                except socket.error as e:
                    print(f"[ERROR] Failed to send broadcast: {e}")
                time.sleep(1)

    def handle_client(self, client_socket: socket.socket, address) -> None:
        """Handle incoming messages from clients and process them accordingly.

        Args:
            client_socket (socket.socket): The client's socket object.
            address (Tuple[str, int]): The client's address.
        """
        client_id = address[1]  # Using port number as unique client ID
        try:
            while not self.shutdown_flag.is_set():
                msg = client_socket.recv(self.INPUT_BUFFER_SIZE)
                if msg:
                    response = self.process_message(client_socket,client_id, msg)
                    if response.startswith("Incorrect"):
                        client_socket.sendall(response.encode(self.FORMAT))
                        self.disconnect_client(client_id)
                    if response:
                        client_socket.sendall(response.encode(self.FORMAT))
                        if response == 'Access Dined!':
                            client_socket.close()
        except socket.timeout:
            print(f"[ERROR] Timeout error from {address} , in handeling client")
        except socket.error as e:
            print(f"[ERROR] Network error from {address}: {e}, in handeling client")
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred: {e}, in handeling client")
        finally:
            self.disconnect_client(client_id)

    def process_message(self,client_socket: socket.socket, client_id: int, msg: bytes) -> str:
        """Processes messages received from clients based on their current state."""
        try:
            first_2byte = msg[0:2]
            massage_type = first_2byte.decode(self.FORMAT)
            # NP = New Client Joins
            if massage_type == 'NP':
                if client_id not in self.clients:
                    return self.register_client(client_socket, client_id, msg[2:].decode(self.FORMAT).strip())
                else:
                    return 'Access Dined!'
            print(msg)
            # Adding Clients to the game
            first_7bytes = msg[:7]
            massage_type = first_7bytes.decode(self.FORMAT)
            # print(massage_type)
            if self.games.active: # if game is on going
                if self.games.players.get(client_id): #for players that play
                    if massage_type == 'waiting' or "True" or "False":
                        return self.games.play(massage_type)

                    elif massage_type == "Incorrect" or massage_type == "Correct":
                        self.games.answers[client_id] = massage_type
                if len(self.games.answers) == len(self.games.players):
                    for client_id in self.games.answers:
                        if self.games.players[client_id] == 'Incorrect':
                            self.disconnect_client(client_id)



            else: #waiting for players
                if self.games.timer!= None:
                    with self.lock:self.games.active = True
                if self.games.players.get(client_id): #if player sighned into game and waite to start
                    if len(self.games.questions) == 0:
                        return "Time to start : "+str(int(self.games.timer) - int(time.time()))
                    else:
                        ttl = str((len(self.games.questions) * 10) // 60)
                        return f"Time to start next Game is : {ttl}"
                else: # if game is not active and not signed , add player
                    self.games.add_player(self.clients[client_id][1], self.clients[client_id][2])
                    return "Time to start : "+'\n'+str(int(self.games.timer + 10))


        except ValueError as ve:
            print(f"Error processing message: {ve}")
        except socket.error as se:
            print(f"Socket error: {se}")
        except Exception as e:
            print(f"An unexpected error occurred: {e} in processing response")

    def register_client(self,client_socket, client_id, name):
        """Registers a new client, ensuring no duplicate registrations."""
        try:
            if any(name == client_info[2] for client_info in self.clients.values()):
                print(f"[ERROR] Duplicate client name detected: {name}")
                return f"[ERROR] Duplicate client name detected: {name}"
            else:
                with self.lock:
                    self.clients[client_id] = [client_socket, client_id, name]
                    welcome_message = f"Join_Server_Successfully"
                    print(f"[NEW CLIENT] {client_id} registered as {name} ,{welcome_message}")
                    return welcome_message
        except ValueError as ve:
            print(f"Error processing message: {ve}")
        except socket.error as se:
            print(f"Socket error: {se}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def disconnect_client(self, client_id):
        """Disconnects a client and removes them from the client list."""
        try:
            if client_id in self.clients:
                with self.lock:
                    if client_id in self.clients:
                        client_socket = self.clients[client_id][0]
                        del self.clients[client_id]
                        print(f"[DISCONNECTED] Client {client_id} disconnected.")
        except socket.error as se:
            print(f"Socket error: {se}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if client_socket:
                client_socket.close()

    def start_tcp_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_server_socket:
            tcp_server_socket.bind((self.SERVER_IP, self.TCP_PORT))
            tcp_server_socket.listen()
            print("TCP Server is listening...")
            while not self.shutdown_flag.is_set():
                try:
                    client_socket, addr = tcp_server_socket.accept() #new client
                    thread = threading.Thread(target=self.handle_client, args=(client_socket, addr)) #new thread for client
                    thread.start()
                except socket.error:
                    if self.shutdown_flag.is_set():
                        break

    def shutdown_server(self):
            """Gracefully shuts down the server."""
            print("Shutting down the server...")
            self.shutdown_flag.set()
            for _, client in self.clients.items():
                client[0].close()
            threading.enumerate()[0].join()
            print("Server has been shut down.")

class TriviaGame:
    def __init__(self):
        self.active = False # Bool Flag to see if game is ongoing True for playing False for waiting for players
        self.players = {}  # Stores player details with their socket: {socket: {"name": "", "score": 0}}
        self.questions = [  ]
        self.current_question = None
        self.current_answer = None
        self.trivia = {}
        self.answers={} #PORT:TRUE/FALSE
        self.game_Lock = threading.Lock()
        self.timer = None

    def add_player(self, client_id, player_name):
        """Add a new player to the game."""
        self.players[client_id] = player_name
        self.timer = time.time() + 3
        print(f"[NEW PLAYER] {player_name}.")
        return f"{player_name} added to the game"

    def remove_player(self, player_socket):
        """Remove a player from the game."""
        if player_socket in self.players:
            del self.players[player_socket]

    def play(self, message):
        """Processes player's answers and updates scores."""
        with self.game_Lock:
            if self.current_answer==None and self.active == True or self.timer<0:
                self.next_round()
            if message == "waiting":
                os.system('cls')
                return "True or False ? :"+self.current_question+'\n'
            elif message == 'False' or message == 'True':
                if message == str(self.current_answer):
                    Answer = "Correct\n"
                else:
                    Answer = "Incorrect\n"
                result = Answer + self.trivia.get(self.questions[0][1])  # (TURE/FALE,QUTION) \n {QUETION:EXPLANITION}
                return result
            else:
                if self.timer+10 < time.time(): # if all player answerd OR 10 seconds passed and time is up
                   self.next_round()
                    #return the results and explanation
                else:
                    return "Time to left :" + str(int(self.timer+10-time.time()))


    def next_round(self):
        if not self.questions:
            self.questions , self.trivia = self.select_questions_sequence()
        else:
            self.questions = self.questions[1:]
        self.current_question = self.questions[0][1]
        self.current_answer = self.questions[0][0]
        self.timer = time.time()


    def reset_game(self):
        """Reset the game state to start over or end the game."""
        self.players.clear()
        self.current_question = None
        self.current_answer = None
        self.timer = None

    def select_questions_sequence(self):
        # Randomly select questions based on the specified counts
        simple_questions = [
            (True, "Harry Potter's parents were named Lily and James."),
            (False, "Hermione Granger is sorted into Ravenclaw house."),
            (True, "Ron Weasley has six siblings."),
            (True, "Severus Snape is the first Potions Master introduced in the series."),
            (True, "Harry Potter has a lightning bolt scar on his forehead."),
            (True, "The headmaster of Hogwarts during Harry's time is Albus Dumbledore."),
            (True, "The Hogwarts Express leaves from Platform 9¾ at King's Cross Station."),
            (False, "Draco Malfoy's patronus is a snake."),
            (True, "The sport played by witches and wizards on broomsticks is called Quidditch."),
            (False, "The Marauder's Map is given to Harry by Professor Snape.")
        ]
        medium_questions = [
            (True, "Neville Longbottom ends up working as a professor at Hogwarts."),
            (True, "Luna Lovegood's father's name is Xenophilius."),
            (False, "The spell 'Levicorpus' is used to unlock doors."),
            (True, "Moaning Myrtle's real name is Myrtle Warren."),
            (False, "The only way to destroy a Horcrux is with basilisk venom."),
            (True, "Sirius Black transforms into a black dog."),
            (False, "Dobby gives Harry Potter the gillyweed in the Triwizard Tournament."),
            (True, "Bellatrix Lestrange is Draco Malfoy's aunt."),
            (False, "The Room of Requirement can only be found by someone who already knows it's there."),
            (False, "Fawkes is a phoenix belonging to Minerva McGonagall."),
            (True, "The Killing Curse is 'Avada Kadavra.'"),
            (True, "The Weasley's house is named The Burrow."),
            (False, "The Half-Blood Prince is a title claimed by Lord Voldemort."),
            (False, "The Triwizard Tournament was held every three years."),
            (True, "A bezoar is a stone taken from the stomach of a cow."),
            (False, "Muggles can see dementors."),
            (True, "The mirror that shows the deepest desire of one's heart is called the Mirror of Erised."),
            (False, "The password to enter the Gryffindor common room is always 'caput draconis.'"),
            (True, "Cornelius Fudge has a lime green bowler hat."),
            (False, "A Patronus is used to ward off Lethifolds.")
        ]
        hard_questions = [
            (False, "Percy Weasley marries Penelope Clearwater."),
            (True, "The Lovegoods publish a magazine called The Quibbler."),
            (True, "Harry's first ever Quidditch position was as a Seeker."),
            (True, "The full name of the Hogwarts ghost Nearly Headless Nick is Sir Nicholas de Mimsy-Porpington."),
            (False, "The giant spider Aragog was acquired by Hagrid from a distant land."),
            (True, "The incantation for producing the Dark Mark is 'Morsmordre.'"),
            (False, "Remus Lupin's patronus is a werewolf."),
            (True, "Dumbledore's full name is Albus Percival Wulfric Brian Dumbledore."),
            (True, "The first password Harry uses for Dumbledore's office is 'Sherbet Lemon.'"),
            (False, "Ginny Weasley's full first name is Virginia.")
        ]
        trivia_explanations = {
            "Harry Potter's parents were named Lily and James.": "True - Lily and James Potter are the names of Harry's parents, as consistently mentioned throughout the series.",
            "Hermione Granger is sorted into Ravenclaw house.": "False - Hermione Granger was sorted into Gryffindor house, not Ravenclaw, although she does embody many qualities typical of Ravenclaws such as intelligence and wit.",
            "Ron Weasley has six siblings.": "True - Ron has five brothers (Bill, Charlie, Percy, Fred, and George) and one sister (Ginny), making six siblings in total.",
            "Severus Snape is the first Potions Master introduced in the series.": "True - Severus Snape is the first Potions Master we meet in the Harry Potter series, teaching the subject at Hogwarts when Harry first attends.",
            "Harry Potter has a lightning bolt scar on his forehead.": "True - Harry received this scar as a baby, when Voldemort's killing curse rebounded off him.",
            "The headmaster of Hogwarts during Harry's time is Albus Dumbledore.": "True - Albus Dumbledore is the headmaster of Hogwarts for the majority of Harry's time at the school.",
            "The Hogwarts Express leaves from Platform 9¾ at King's Cross Station.": "True - Students board the Hogwarts Express at Platform 9¾, which is magically concealed from Muggle view.",
            "Draco Malfoy's patronus is a snake.": "False - There is no record of Draco Malfoy's Patronus in the Harry Potter books. Additionally, casting a Patronus is thought to be beyond Draco's capabilities as it requires positive memories and genuine happiness.",
            "The sport played by witches and wizards on broomsticks is called Quidditch.": "True - Quidditch is the popular sport among witches and wizards, played on broomsticks.",
            "The Marauder's Map is given to Harry by Professor Snape.": "False - The Marauder's Map is given to Harry by Fred and George Weasley, not Snape.",
            "Neville Longbottom ends up working as a professor at Hogwarts.": "True - In the epilogue and interviews, it is revealed that Neville becomes the professor of Herbology at Hogwarts.",
            "Luna Lovegood's father's name is Xenophilius.": "True - Luna's father is indeed named Xenophilius Lovegood, who is the editor of the Quibbler.",
            "The spell 'Levicorpus' is used to unlock doors.": "False - 'Levicorpus' is a spell used to lift someone into the air by their ankle. 'Alohomora' is used to unlock doors.",
            "Moaning Myrtle's real name is Myrtle Warren.": "True - This is revealed in Pottermore and other interviews with J.K. Rowling.",
            "The only way to destroy a Horcrux is with basilisk venom.": "False - While basilisk venom is one way to destroy a Horcrux, there are other methods as well, such as the Sword of Gryffindor imbued with basilisk venom, Fiendfyre, or other extremely destructive magical means.",
            "Sirius Black transforms into a black dog.": "True - Sirius Black's Animagus form is indeed a large black dog.",
            "Dobby gives Harry Potter the gillyweed in the Triwizard Tournament.": "False - In the book 'Harry Potter and the Goblet of Fire,' it is actually Neville Longbottom who provides Harry with the gillyweed, thanks to a tip from Dobby; however, in the movie adaptation, Dobby is the one who gives Harry the gillyweed.",
            "Bellatrix Lestrange is Draco Malfoy's aunt.": "True - Bellatrix Lestrange is the sister of Narcissa Malfoy, who is Draco's mother, making her his aunt.",
            "The Room of Requirement can only be found by someone who already knows it's there.": "False - The Room of Requirement appears when a person is in great need of it and walks past its location three times while concentrating on that need.",
            "Fawkes is a phoenix belonging to Minerva McGonagall.": "False - Fawkes is Albus Dumbledore’s phoenix, not Minerva McGonagall's.",
            "The Killing Curse is 'Avada Kadavra.'": "True - 'Avada Kedavra' is the correct incantation for the Killing Curse, one of the three Unforgivable Curses.",
            "The Weasley's house is named The Burrow.": "True - The Weasley family home is affectionately known as The Burrow.",
            "The Half-Blood Prince is a title claimed by Lord Voldemort.": "False - The title 'Half-Blood Prince' is actually claimed by Severus Snape.",
            "The Triwizard Tournament was held every three years.": "False - The Triwizard Tournament was originally intended to be held every five years.",
            "A bezoar is a stone taken from the stomach of a cow.": "True - A bezoar is a stone from the stomach of a goat, which can cure most poisons (it is often mistaken regarding the animal but correctly, it's from a goat).",
            "Muggles can see dementors.": "False - Muggles cannot see dementors, but they can feel the effects of their presence such as cold and despair.",
            "The mirror that shows the deepest desire of one's heart is called the Mirror of Erised.": "True - The Mirror of Erised shows the user's deepest and most desperate desire of their heart.",
            "The password to enter the Gryffindor common room is always 'caput draconis.'": "False - The password to the Gryffindor common room changes frequently; 'Caput Draconis' is just one of the passwords used.",
            "Cornelius Fudge has a lime green bowler hat.": "True - Cornelius Fudge, the Minister for Magic, is often described as wearing a lime green bowler hat.",
            "A Patronus is used to ward off Lethifolds.": "False - A Patronus is used to ward off Dementors, not Lethifolds, although it's mentioned that a Patronus could theoretically defend against a Lethifold since they are both dark creatures.",
            "Percy Weasley marries Penelope Clearwater.": "False - Percy Weasley marries a woman named Audrey, not Penelope Clearwater.",
            "The Lovegoods publish a magazine called The Quibbler.": "True - Xenophilius Lovegood is the editor of The Quibbler, a magazine that publishes odd and unorthodox stories.",
            "Harry's first ever Quidditch position was as a Seeker.": "True - Harry Potter was first recruited to play as a Seeker on the Gryffindor Quidditch team.",
            "The full name of the Hogwarts ghost Nearly Headless Nick is Sir Nicholas de Mimsy-Porpington.": "True - This is the full name of the ghost known as Nearly Headless Nick, who haunts the Gryffindor Tower and other parts of Hogwarts.",
            "The giant spider Aragog was acquired by Hagrid from a distant land.": "False - Aragog was actually a gift to Hagrid when he was a student at Hogwarts; he didn't acquire Aragog from a distant land but from a fellow student.",
            "The incantation for producing the Dark Mark is 'Morsmordre.'": "True - 'Morsmordre' is the incantation used to conjure the Dark Mark, the symbol used by Voldemort and his followers.",
            "Remus Lupin's patronus is a werewolf.": "False - Although Remus Lupin is a werewolf, his Patronus is actually a wolf, not a werewolf. Patronuses typically take the form of an animal that represents the caster, not their afflicted form.",
            "Dumbledore's full name is Albus Percival Wulfric Brian Dumbledore.": "True - This is the full name of Albus Dumbledore, the headmaster of Hogwarts.",
            "The first password Harry uses for Dumbledore's office is 'Sherbet Lemon.'": "True - 'Sherbet Lemon' is indeed one of the passwords for Dumbledore’s office that Harry uses. This reflects Dumbledore’s fondness for Muggle sweets.",
            "Ginny Weasley's full first name is Virginia.": "False - Ginny's full first name is Ginevra, not Virginia."
        }
        selected_simple = random.sample(simple_questions, 3)
        selected_medium = random.sample(medium_questions, 4)
        selected_hard = random.sample(hard_questions, 3)
        self.questions = selected_simple + selected_medium + selected_hard
        for question in self.questions:
            self.trivia = trivia_explanations.get(question[0])
            return self.questions ,trivia_explanations

if __name__ == '__main__':
    server = Server()
    server_thread = threading.Thread(target=server.start_tcp_server)
    server_thread.start()
    offer_thread = threading.Thread(target=server.broadcast_offers)
    offer_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown_server()
        server_thread.join()
        offer_thread.join()  # Ensure this thread is also cleanly shutdown

