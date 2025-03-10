from snippets.lab4.custom_client import CustomClient
from snippets.lab4.users import Token
from snippets.lab4.example1_presentation import serialize, deserialize, Request, Response
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


def main():
    parser = argparse.ArgumentParser(description="MindRoll RPC Client CLI (Minimal Register + Login)")
    parser.add_argument("server_ip", help="Server IP address")
    parser.add_argument("server_port", type=int, help="Server port number")
    parser.add_argument("command", help="Command to execute",
                        choices=[
                            "register", "login",
                            "create_room", "join_room", "call_number",
                            "reveal_result", "get_game_state",
                            "load_token"
                        ])
    parser.add_argument("--room", help="Room ID")
    parser.add_argument("--user", help="Username")
    parser.add_argument("--password", help="Password")
    parser.add_argument("--number", type=int, help="Number to call")
    parser.add_argument("--token-file", help="Path to token file")

    args = parser.parse_args()

    client = MindRollClient((args.server_ip, args.server_port))

    print("\n=== MindRoll Client Ready ===")
    print("Available commands:")
    print("  register <user> <pass>")
    print("  login <user> <pass>")
    print("  create_room <room>")
    print("  join_room <room> <user>")
    print("  call_number <room> <user> <number>")
    print("  reveal_result <room> <user>")
    print("  get_game_state <room>")
    print("  load_token <file>")
    print("  exit")

    # 如果在启动时就带了 "load_token" 并且 --token-file，则先载入
    if args.command == "load_token" and args.token_file:
        with open(args.token_file, 'r') as f:
            data = json.load(f)
            if 'token' in data:
                client.token = data['token']
                print(f"✅ Token loaded from {args.token_file}")
            else:
                print(f"❌ Invalid token file (no 'token' key).")

    # 命令行循环
    while True:
        cmd_line = input("\nEnter command: ").strip()
        if not cmd_line:
            continue
        parts = cmd_line.split()
        cmd, *params = parts

        try:
            if cmd == "register":
                # register <username> <password>
                if len(params) < 2:
                    print("Usage: register <username> <password>")
                    continue
                username, password = params[0], params[1]
                client.register(username, password)

            elif cmd == "login":
                if len(params) < 2:
                    print("Usage: login <username> <password>")
                    continue
                client.login(params[0], params[1])

            elif cmd == "create_room":
                if len(params) < 1:
                    print("Usage: create_room <room_id>")
                    continue
                client.create_room(params[0])

            elif cmd == "join_room":
                if len(params) < 2:
                    print("Usage: join_room <room_id> <username>")
                    continue
                client.join_room(params[0], params[1])

            elif cmd == "call_number":
                if len(params) < 3:
                    print("Usage: call_number <room_id> <username> <number>")
                    continue
                client.call_number(params[0], params[1], params[2])

            elif cmd == "reveal_result":
                if len(params) < 2:
                    print("Usage: reveal_result <room_id> <username>")
                    continue
                client.reveal_result(params[0], params[1])

            elif cmd == "get_game_state":
                if len(params) < 1:
                    print("Usage: get_game_state <room_id>")
                    continue
                client.get_game_state(params[0])

            elif cmd == "load_token":
                if len(params) < 1:
                    print("Usage: load_token <token_file>")
                    continue
                token_file = params[0]
                try:
                    with open(token_file, 'r') as f:
                        data = json.load(f)
                        if 'token' in data:
                            client.token = data['token']
                            print(f"✅ Token loaded from {token_file}")
                        else:
                            print(f"❌ Invalid token file (no 'token' key).")
                except FileNotFoundError:
                    print(f"❌ Token file not found: {token_file}")
                except json.JSONDecodeError:
                    print(f"❌ Invalid token file format")

            elif cmd == "exit":
                print("Exiting client...")
                client.close()
                break
            else:
                print("❌ Invalid command or parameters!")
        except KeyboardInterrupt:
            print("\nClient shutting down.")
            client.close()
            break
        except Exception:
            traceback.print_exc()
            print("❌ An error occurred.")


if __name__ == "__main__":
    main()
