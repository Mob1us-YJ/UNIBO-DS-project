# src/server/main.py
import sys
import os
# import src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.server.rpc_server import MindRollServer

if __name__ == '__main__':
    server = MindRollServer(port=8080)
    print("MindRoll Server is running...")
    server.start()