import unittest
from src.client.rpc_client import MindRollClient
from src.server.rpc_server import MindRollServer
import threading
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MindRollServer(port=8083)
        cls.server_thread = threading.Thread(target=cls.server.start)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server_thread.join()

    def test_full_game_flow(self):
        client1 = MindRollClient(("127.0.0.1", 8083))
        client1.register("player1", "password123")
        client1.login("player1", "password123")
        client1.create_room("room1")
        client1.join_room("room1", "player1")

        client2 = MindRollClient(("127.0.0.1", 8083))
        client2.register("player2", "password123")
        client2.login("player2", "password123")
        client2.join_room("room1", "player2")

        client1.call_number("room1", "player1", 10)
        client2.call_number("room1", "player2", 15)
        result = client1.reveal_result("room1", "player1")
        self.assertIn("result_str", result)