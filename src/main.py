# src/server/main.py
from server.rpc_server import MindRollServer

if __name__ == '__main__':
    server = MindRollServer(port=8080)
    print("MindRoll Server is running...")
    server.start()