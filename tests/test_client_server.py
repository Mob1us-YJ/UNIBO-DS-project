import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from src.client.rpc_client import MindRollClient
from src.server.rpc_server import MindRollServer
import threading

class TestClientServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MindRollServer(port=8082)
        cls.server_thread = threading.Thread(target=cls.server.start)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server_thread.join()

    def test_register_and_login(self):
        client = MindRollClient(("127.0.0.1", 8082))
        response = client.register("test_user", "password123")
        self.assertIsNone(response.error)
        response = client.login("test_user", "password123")
        self.assertIsNone(response.error)
        self.assertIsNotNone(client.token)