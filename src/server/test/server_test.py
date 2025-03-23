import unittest
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.server.backup_server import BackupServer
from src.server.rpc_server import MindRollServer


import unittest
import threading
import time

"""Test if backup server can take over when main server fails."""
class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.main_server = MindRollServer()
        self.backup_server = BackupServer()
        self.main_server.set_backup_server(self.backup_server)

    def test_failover(self):
        # 
        main_thread = threading.Thread(target=self.main_server.start)
        main_thread.start()
        time.sleep(1)  

 
        self.main_server.running = False
        time.sleep(1)  


        backup_thread = threading.Thread(target=self.backup_server.start)
        backup_thread.start()
        time.sleep(1) 

        self.assertTrue(self.backup_server.running)

if __name__ == "__main__":
    unittest.main()