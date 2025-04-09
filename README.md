# UNIBO-DS-project
Final Project of distributed-system 2024
# 🎲 MindRoll: A Multiplayer Dice Game

MindRoll is a distributed, turn-based multiplayer dice game implemented in Python. It demonstrates core principles of distributed systems such as authentication, state synchronization, remote procedure calls (RPC), and client-server architecture.

## 🚀 Features

- 🎮 Pygame-based graphical user interface
- 👥 Multiplayer support with room-based logic
- 🔐 User registration and login with secure password hashing
- 🛡️ Token-based authentication (with expiration)
- 🧠 Game logic: dice rolling, turn-based number calling, reveal logic
- 💾 MongoDB persistent storage for users and tokens
- 🔁 Reconnection support and token cleanup via TTL

## 🧰 Requirements

- Python 3.10+
- MongoDB running locally or remotely

Install all dependencies with:

```bash
pip install -r requirements.txt
```
## Running the game
1. Start MongoDB
Make sure MongoDB is running. 
2. Run the Game Server
```bash
python -m src.server.rpc_server
```
This will start the server on localhost:8080.

3. Run the Client (in a new terminal window)
```bash
python -m src.client.ui
```
## Authors
👤 Authors
Tianyu Qu

Yiming Li

Jing Yang
