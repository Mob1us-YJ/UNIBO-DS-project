import json
import sys
import traceback
import threading

from src.client.customer_client import CustomClient
from src.common.users import Token
from src.common.utils import serialize, deserialize, Request, Response


class MindRollClient(CustomClient):
    """A custom client class for MindRoll that properly manages network connections.
    """

    def __init__(self, server_address):
        super().__init__(server_address)
        self.token = None  # save token

    def send_request(self, method, *args):
        """
        Send an RPC request to the server.
        """
        if not self.connected:
            self.connect()

        # If not register/login, with token
        metadata = {}
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
         register <username> <password>.
        """
        return self.send_request("register", username, password)

    def login(self, username, password):
        """
        login <username> <password>.
        Return { 'token': 'xxx-uuid' }, save self.token.
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
        create_room <room_id>.
        """
        print(f"🏠 Creating room: {room_id}")
        return self.send_request("create_room", room_id)

    def join_room(self, room_id, player_name):
        """
        join_room <room_id> <player_name>.
        """
        print(f"👤 {player_name} is joining room: {room_id}")
        return self.send_request("join_room", room_id, player_name)

    def call_number(self, room_id, player_name, number):
        """
        call_number <room_id> <player_name> <number>.
        """
        print(f"🎲 {player_name} calls number {number} in room {room_id}")
        return self.send_request("call_number", room_id, player_name, number)

    def reveal_result(self, room_id, player_name):
        """
        reveal_result <room_id> <player_name>.
        """
        print(f"📢 {player_name} is revealing the result in room {room_id}")
        return self.send_request("reveal_result", room_id, player_name)

    def get_game_state(self, room_id):
        """
        get_game_state <room_id>.
        """
        print(f"📊 Fetching game state for room {room_id}")
        return self.send_request("get_game_state", room_id)

    # ---------------------- 1) leave room ----------------------
    def leave_room(self, room_id, player_name):
        """
        leave_room <room_id> <player_name>.
        """
        print(f"🚪 {player_name} is leaving room {room_id}")
        return self.send_request("leave_room", room_id, player_name)

    # ---------------------- 2) Reconnect ----------------------
    def reconnect(self, room_id, player_name):
        """
        reconnect <room_id> <player_name>.
        """
        print(f"🔄 {player_name} is trying to reconnect to room {room_id}")
        return self.send_request("reconnect", room_id, player_name)
