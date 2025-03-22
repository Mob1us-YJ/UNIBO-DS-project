import json
import sys
import traceback
import threading

from src.client.customer_client import CustomClient
from src.common.users import Token
from src.common.utils import serialize, deserialize, Request, Response


class MindRollClient(CustomClient):
    """
    客户端：继承自 CustomClient，实现最简的注册 (username, password) + 登录，
    并支持带 token 的后续请求。
    """

    def __init__(self, server_address):
        super().__init__(server_address)
        self.token = None  # 用于存储 token 字符串

    #     self.broadcast_thread = None  # 用于接收广播消息的线程
    #     self.running = True
    #     self.broadcast_callback = None  # 广播消息的回调函数

    # def start_broadcast_listener(self):
    #     """
    #     启动广播消息监听线程。
    #     """
    #     self.broadcast_thread = threading.Thread(target=self.listen_for_broadcasts)
    #     self.broadcast_thread.daemon = True  # 设置为守护线程，主程序退出时自动结束
    #     self.broadcast_thread.start()
    
    # def listen_for_broadcasts(self):
    #     """监听服务器的广播消息"""
    #     while self.running:
    #         try:
    #             if not self.connected:
    #                 self.connect()

    #             # 接收服务器广播的消息
    #             data = self.sock.recv(4096).decode('utf-8')
    #             if data:
    #                 print(f"📨 Received broadcast: {data}")
    #                 response = deserialize(data)
    #                 self.handle_broadcast(response)
    #         except Exception as e:
    #             print(f"❌ Error receiving broadcast: {e}")
    #             break
    
    # def set_broadcast_callback(self, callback):
    #         """设置广播消息的回调函数"""
    #         self.broadcast_callback = callback

    # def handle_broadcast(self, response):
    #     """处理服务器广播的消息"""
    #     if isinstance(response, Response) and response.result:
    #         # 假设广播的消息格式与 reveal_result 的响应一致
    #         game_state = response.result
    #         if "players" in game_state and "result_str" in game_state:
    #             # 调用回调函数，将消息传递给 UI
    #             if self.broadcast_callback:
    #                 self.broadcast_callback(game_state)

    # def stop_broadcast_listener(self):
    #     """停止广播监听线程"""
    #     self.running = False
    #     if self.broadcast_thread:
    #         self.broadcast_thread.join()  


    def send_request(self, method, *args):
        """
        发送 RPC 请求到服务器。
        如果方法不是 "register" 或 "login" 并且已经有 self.token，则自动在 metadata 里携带 token。
        """
        if not self.connected:
            self.connect()

        # 如果不是 register/login，这里就要带上 token
        metadata = {}
        if method not in ["register", "login"] and self.token:
            metadata = {"token": {"token": self.token}}

        # 创建 Request 对象
        request_obj = Request(method, args, metadata)
        serialized_req = serialize(request_obj)
        print(f"📤 Sending request: {serialized_req}")

        try:
            with self.lock:
                self.sock.sendall(serialized_req.encode('utf-8'))
                response_data = self.sock.recv(4096).decode('utf-8')
                print(f"📥 Received response: {response_data}")

                response = deserialize(response_data)
                if isinstance(response, Response) and response.error:
                    print(f"❌ Server Error: {response.error}")
                else:
                    print(f"✅ Response: {response.result}")

                return response
        except Exception as e:
            print(f"❌ Error during RPC request: {e}")
            return None

    # ---------------------- Register & Login ----------------------
    def register(self, username, password):
        """
        发起注册请求: register <username> <password>.
        """
        return self.send_request("register", username, password)

    def login(self, username, password):
        """
        发起登录请求: login <username> <password>.
        如果成功返回 { 'token': 'xxx-uuid' }，则客户端记住 self.token.
        """
        resp = self.send_request("login", username, password)
        if resp and resp.result and "token" in resp.result:
            self.token = resp.result["token"]
            print(f"✅ Logged in! token={self.token}")
        else:
            print("❌ Login failed or server error")
        return resp

    # ---------------------- Game Commands ----------------------
    def create_room(self, room_id):
        """
        创建游戏房间: create_room <room_id>.
        """
        print(f"🏠 Creating room: {room_id}")
        return self.send_request("create_room", room_id)

    def join_room(self, room_id, player_name):
        """
        加入游戏房间: join_room <room_id> <player_name>.
        """
        print(f"👤 {player_name} is joining room: {room_id}")
        return self.send_request("join_room", room_id, player_name)

    def call_number(self, room_id, player_name, number):
        """
        喊数: call_number <room_id> <player_name> <number>.
        """
        print(f"🎲 {player_name} calls number {number} in room {room_id}")
        return self.send_request("call_number", room_id, player_name, number)

    def reveal_result(self, room_id, player_name):
        """
        揭示结果: reveal_result <room_id> <player_name>.
        """
        print(f"📢 {player_name} is revealing the result in room {room_id}")
        return self.send_request("reveal_result", room_id, player_name)

    def get_game_state(self, room_id):
        """
        获取游戏状态: get_game_state <room_id>.
        """
        print(f"📊 Fetching game state for room {room_id}")
        return self.send_request("get_game_state", room_id)

    # ---------------------- 1) 离开房间 ----------------------
    def leave_room(self, room_id, player_name):
        """
        离开房间: leave_room <room_id> <player_name>.
        - 仅在游戏结束 (server端 winner != None) 的情况下才会成功.
        """
        print(f"🚪 {player_name} is leaving room {room_id}")
        return self.send_request("leave_room", room_id, player_name)

    # ---------------------- 2) 断线重连 ----------------------
    def reconnect(self, room_id, player_name):
        """
        断线重连: reconnect <room_id> <player_name>.
        - 必须在玩家断线后、且120秒内调用，否则无效.
        """
        print(f"🔄 {player_name} is trying to reconnect to room {room_id}")
        return self.send_request("reconnect", room_id, player_name)
