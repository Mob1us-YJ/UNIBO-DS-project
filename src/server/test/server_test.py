import unittest
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.server.backup_server import BackupServer
from src.server.rpc_server import MindRollServer


import unittest
import threading
import time


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.main_server = MindRollServer()
        self.backup_server = BackupServer()
        self.main_server.set_backup_server(self.backup_server)

    def test_failover(self):
        # 启动主服务器
        main_thread = threading.Thread(target=self.main_server.start)
        main_thread.start()
        time.sleep(1)  # 等待主服务器启动

        # 模拟主服务器故障
        self.main_server.running = False
        time.sleep(1)  # 等待主服务器停止

        # 启动备用服务器
        backup_thread = threading.Thread(target=self.backup_server.start)
        backup_thread.start()
        time.sleep(1)  # 等待备用服务器启动

        # 验证备用服务器是否接管
        self.assertTrue(self.backup_server.running)

if __name__ == "__main__":
    unittest.main()