import socket
import threading
import json
import random
import traceback
from datetime import datetime, timedelta

from src.common.utils import Request, Response, serialize, deserialize
from src.common.users.impl import InMemoryUserDatabase, InMemoryAuthenticationService
from src.common.users import Role, Token, Credentials, User

class MindRollServer:
    """
    A custom TCP server for MindRoll game logic, with a minimal register & login approach.
    All new users are assigned Role.USER automatically.
    Supports multiplayer games where players take turns in the order they join.
    """

    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        # InMemory DB & Auth
        self.__user_db = InMemoryUserDatabase(debug=True)
        self.__auth_service = InMemoryAuthenticationService(self.__user_db, debug=True)

        # Store game rooms
        self.games = {}  # { room_id: { "players": {...}, "players_order": [...], "current_turn": ..., "called_number": ..., "winner": ... } }

    def start(self):
        """Start listening on the configured host+port."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f"MindRoll Server listening on {self.host}:{self.port}")

        try:
            while self.running:
                client_socket, address = self.server_socket.accept()
                print(f"Client connected from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
        except (KeyboardInterrupt, OSError):
            pass

        self.server_socket.close()
        print("MindRoll Server stopped")

    def handle_client(self, client_socket):
        """Handle one client's requests in a loop."""
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    print("Client disconnected")
                    break

                raw_str = data.decode('utf-8').strip()
                print("Received raw data:", raw_str)

                try:
                    request_dict = json.loads(raw_str)
                    request_obj = Request(
                        name=request_dict["name"],
                        args=request_dict.get("args", []),
                        metadata=request_dict.get("metadata", {})
                    )
                except Exception as e:
                    print("Failed to parse request:", e)
                    error_resp = Response(None, f"Parse Error: {e}")
                    self.send_response(client_socket, error_resp)
                    continue

                try:
                    response_obj = self.__handle_request(request_obj)
                except Exception as e:
                    traceback.print_exc()
                    response_obj = Response(None, str(e))

                self.send_response(client_socket, response_obj)
        finally:
            client_socket.close()

    def send_response(self, client_socket, response_obj):
        """Serialize and send the Response object."""
        serialized = serialize(response_obj)
        client_socket.sendall(serialized.encode('utf-8'))

    # ------------------- register -------------------
    def register(self, request: Request) -> Response:
        """
        Minimal: register <username> <password>
        All new users are assigned Role.USER.
        """
        if len(request.args) < 2:
            return Response(None, "Usage: register <username> <password>")
        
        username = request.args[0]
        password = request.args[1]

        new_user = User(
            username=username,
            emails="N/A",        # no emails needed
            full_name=username,
            role=Role.USER,       # always user
            password=password
        )

        try:
            self.__user_db.add_user(new_user)
            return Response(f"Register success for {username}", None)
        except ValueError as e:
            return Response(None, str(e))

    # ------------------- login -------------------
    def login(self, request: Request) -> Response:
        if len(request.args) < 2:
            return Response(None, "Usage: login <username> <password>")

        username, password = request.args[0], request.args[1]
        duration = timedelta(hours=1)

        try:
            token_obj = self.__auth_service.authenticate(Credentials(username, password), duration)
            return Response({"token": token_obj.signature}, None)
        except ValueError as e:
            return Response(None, str(e))

    # ------------------- auth check -------------------
    def __check_authorization(self, request, required_role: Role = Role.USER):
        """Check token from request.metadata['token']['token'], validate and compare role."""
        if 'token' not in request.metadata:
            raise ValueError("Authentication required (no token)")

        token_dict = request.metadata['token']
        if not isinstance(token_dict, dict) or 'token' not in token_dict:
            raise ValueError("Invalid token format in metadata")

        token_str = token_dict['token']
        token_obj = self.__auth_service.validate_token_by_str(token_str)
        if not token_obj:
            raise ValueError("Invalid or expired token")

        if required_role != Role.USER and token_obj.user.role != required_role:
            raise ValueError(f"Operation requires {required_role}, but user role is {token_obj.user.role}")

        return token_obj

    # ------------------- dispatch RPC -------------------
    def __handle_request(self, request: Request):
        if request.name == "register":
            return self.register(request)
        elif request.name == "login":
            return self.login(request)
        elif request.name == "create_room":
            return self.create_room(request)
        elif request.name == "join_room":
            return self.join_room(request)
        elif request.name == "call_number":
            return self.call_number(request)
        elif request.name == "reveal_result":
            return self.reveal_result(request)
        elif request.name == "get_game_state":
            return self.get_game_state(request)
        else:
            raise ValueError(f"Unknown method: {request.name}")

    # --------------- Game logic ---------------
    def create_room(self, request):
        room_id = request.args[0]
        if room_id in self.games:
            return Response(None, "Room already exists")

        self.games[room_id] = {
            "players": {},         # { username: {dice_number, dice_color, score} }
            "players_order": [],   # Explicit join order
            "current_turn": None,
            "called_number": None,
            "winner": None
        }
        return Response(f"Room {room_id} created successfully", None)

    def join_room(self, request):
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        room_id, req_player_name = request.args
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        if req_player_name != real_username:
            return Response(None, f"Token mismatch. Must join as {real_username}")

        game = self.games[room_id]
        if req_player_name in game["players"]:
            return Response(None, "Player already in room")

        dice_number = random.randint(1, 6)
        dice_color = random.choice(["red", "yellow", "green", "blue", "black"])
        game["players"][req_player_name] = {
            "dice_number": dice_number,
            "dice_color": dice_color,
            "score": 0
        }

        # Record the order of joining.
        if "players_order" not in game:
            game["players_order"] = []
        game["players_order"].append(req_player_name)

        # If no one is in turn yet, set current_turn.
        if game["current_turn"] is None:
            game["current_turn"] = req_player_name
            game["called_number"] = max(3 * len(game["players"]) + 1, 7)

        return Response(f"{req_player_name} joined room {room_id}, dice: {dice_number} {dice_color}", None)

    def call_number(self, request):
        room_id, req_player_name, number = request.args
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        if game["current_turn"] != req_player_name:
            return Response(None, "Not your turn to call")

        number = int(number)
        if number <= game["called_number"]:
            return Response(None, "Called number must be greater than the previous one")

        # Update called number.
        game["called_number"] = number

        # Rotate turn based on players_order.
        players = game.get("players_order", [])
        if not players:
            return Response(None, "No players in room")
        i = players.index(req_player_name)
        next_i = (i + 1) % len(players)
        next_turn = players[next_i]
        game["current_turn"] = next_turn

        return Response(f"{req_player_name} called {number}, next turn: {next_turn}", None)

    def reveal_result(self, request):
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        room_id, req_player_name = request.args
        # 首先检查 token 与请求的用户名一致
        if req_player_name != real_username:
            return Response(None, f"Token mismatch, must reveal_result as {real_username}")

        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        # 新要求：必须由当前轮到的玩家调用 reveal_result
        if req_player_name != game["current_turn"]:
            return Response(None, f"Only the current turn player ({game['current_turn']}) can reveal the result.")

        # 根据游戏规则计算总点数
        total_sum = sum(p["dice_number"] for p in game["players"].values())
        # 这里示例规则：如果叫数大于总点数，则当前玩家输，否则赢
        if game["called_number"] < total_sum:
            result_str = f"{req_player_name} loses! (Called number {game['called_number']} > total dice sum {total_sum})"
        else:
            result_str = f"{req_player_name} wins! (Called number {game['called_number']} <= total dice sum {total_sum})"

        return Response(result_str, None)

    def get_game_state(self, request):
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        room_id = request.args[0]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        return Response(self.games[room_id], None)

    def stop(self):
        self.running = False
        self.server_socket.close()


if __name__ == '__main__':
    server = MindRollServer(port=8080)
    print("MindRoll Server is running with a minimal register <username> <password> approach and sequential turn calling.")
    server.start()
