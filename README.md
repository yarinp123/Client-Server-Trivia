# Trivia Game - Client-Server Architecture

A real-time multiplayer trivia game where players connect to a server and compete by answering true/false questions. The game is built using Python's socket programming for network communication.

## Features

- **Multiplayer Support**: Multiple clients can connect to a single server
- **True/False Questions**: Players answer true/false trivia questions
- **Real-time Updates**: Immediate feedback on answers and game progress
- **Automatic Matchmaking**: Server broadcasts availability for clients to connect
- **Score Tracking**: Keep track of player scores during the game

## Prerequisites

- Python 3.x
- No additional packages required (uses built-in libraries only)

## Project Structure

- `Server.py`: The game server that manages connections and game logic
- `Client.py`: The client application that players use to connect to the server

## How to Run

### Starting the Server

1. Navigate to the project directory
2. Run the server with Python:
   ```
   python Server.py
   ```
3. The server will start and begin broadcasting its availability

### Joining as a Client

1. Open a new terminal window
2. Navigate to the project directory
3. Run the client with Python:
   ```
   python Client.py
   ```
4. When prompted, enter your player name
5. The client will automatically search for and connect to an available server

### Playing the Game

1. Once connected, wait for the game to start
2. When a question appears, type 'T' for True or 'F' for False and press Enter
3. The server will provide immediate feedback on your answer
4. The game continues with multiple rounds of questions
5. The player with the highest score at the end wins

## Game Rules

- Each correct answer awards 1 point
- Incorrect answers may result in elimination (depending on server configuration)
- The game continues for a set number of rounds
- The player with the highest score at the end wins

## Troubleshooting

- Ensure no firewall is blocking the ports (UDP 13117 for discovery, TCP 2112 for game)
- Make sure only one server is running on the same network
- All players should be on the same local network for discovery to work
- If connection fails, verify the server's IP address and port

## Customization

You can modify the following in the code:
- Server port numbers in both `Server.py` and `Client.py`
- Number of questions per game in `Server.py`
- Time limits for answering questions in `Server.py`

## License

This project is for educational purposes.
