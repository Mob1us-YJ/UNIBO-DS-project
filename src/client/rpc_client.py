from src.client.customer_client import CustomClient
from src.common.users import Token
from src.common.utils import serialize, deserialize, Request, Response

import argparse
import json
import sys
import traceback

class MindRollClient(CustomClient):
    """客户端，继承自 CustomClient，实现最简的注册 (username, password) + 登录，以及带 token 的后续请求。"""

    def __init__(self, server_address):
        super().__init__(server_address)
        self.token = None  # 用于存储 token 字符串

    def send_request(self, method, *args):
        """
        发送 RPC 请求到服务器。
        如果方法不是 "register" 或 "login" 并且我们有 self.token，则将其放入 metadata['token']['token']。
        """
        if not self.connected:
            self.connect()

        metadata = {}
        # 除了 register / login，其它都需要 token
        if method not in ["register", "login"] and self.token:
            metadata = {"token": {"token": self.token}}

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
        发送 register RPC，只需要 [username, password]。
        """
        return self.send_request("register", username, password)

    def login(self, username, password):
        """
        向服务器发送 login RPC: [username, password]。
        如果成功返回 { 'token': 'xxx-uuid' }，则客户端记住 self.token。
        """
        resp = self.send_request("login", username, password)
        if resp and resp.result and "token" in resp.result:
            self.token = resp.result["token"]
            print(f"✅ Logged in! token={self.token}")
        else:
            print("❌ Login failed or server error")

    # ---------------------- Game Commands ----------------------
    def create_room(self, room_id):
        print(f"🏠 Creating room: {room_id}")
        self.send_request("create_room", room_id)

    def join_room(self, room_id, player_name):
        print(f"👤 {player_name} is joining room: {room_id}")
        self.send_request("join_room", room_id, player_name)

    def call_number(self, room_id, player_name, number):
        print(f"🎲 {player_name} calls number {number} in room {room_id}")
        self.send_request("call_number", room_id, player_name, number)

    def reveal_result(self, room_id, player_name):
        print(f"📢 {player_name} is revealing the result in room {room_id}")
        self.send_request("reveal_result", room_id, player_name)

    def get_game_state(self, room_id):
        print(f"📊 Fetching game state for room {room_id}")
        self.send_request("get_game_state", room_id)