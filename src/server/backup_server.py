# backup_server.py
import threading
import socket

class BackupServer:
    def __init__(self, host='0.0.0.0', port=8081):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.games = {}  # 游戏房间数据

    def update_games(self, games):
        """从主服务器同步游戏数据"""
        self.games = games
        print("Backup Server: Games data updated") 

    def start(self):
        """启动备份服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f"Backup Server listening on {self.host}:{self.port}")

        try:
            while self.running:
                client_socket, address = self.server_socket.accept()
                print(f"Client connected from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
        except (KeyboardInterrupt, OSError):
            pass

        self.server_socket.close()
        print("Backup Server stopped")

    # 其他备份服务器逻辑...