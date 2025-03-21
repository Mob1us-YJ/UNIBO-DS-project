import socket
import threading
import json
import random
import traceback
import time
from datetime import datetime, timedelta

from snippets.lab4.example1_presentation import Request, Response, serialize, deserialize
from snippets.lab4.users.impl import InMemoryUserDatabase, InMemoryAuthenticationService
from snippets.lab4.users import Role, Token, Credentials, User

class MindRollServer:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        self.__user_db = InMemoryUserDatabase(debug=True)
        self.__auth_service = InMemoryAuthenticationService(self.__user_db, debug=True)

        # 房间数据结构: { room_id: {
        #   "players": { username: {dice_number, dice_color, score, connected, disconnected_time } },
        #   "players_order": [...],
        #   "current_turn": ...,
        #   "called_number": None or int,
        #   "winner": None or username
        # } }
        self.games = {}

    def start(self):
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
        user_token_str = None
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

                # 若带token则记录下来
                if 'token' in request_obj.metadata:
                    token_dict = request_obj.metadata['token']
                    if 'token' in token_dict:
                        user_token_str = token_dict['token']

                try:
                    response_obj = self.__handle_request(request_obj)
                except Exception as e:
                    traceback.print_exc()
                    response_obj = Response(None, str(e))

                self.send_response(client_socket, response_obj)
        finally:
            # 断开时标记断线
            if user_token_str:
                self.mark_player_disconnected(user_token_str)
            client_socket.close()

    def send_response(self, client_socket, response_obj):
        serialized = serialize(response_obj)
        client_socket.sendall(serialized.encode('utf-8'))

    # ==================== 标记玩家断开 ====================
    def mark_player_disconnected(self, token_str):
        """
        如果房间只有该玩家 => 删房
        否则标记该玩家connected=False, 记录断线时间
        """
        token_obj = self.__auth_service.validate_token_by_str(token_str)
        if not token_obj:
            return
        username = token_obj.user.username

        for room_id, game in list(self.games.items()):
            if username in game["players"]:
                if len(game["players"]) == 1:
                    del self.games[room_id]
                    print(f"Room {room_id} removed because the only player ({username}) disconnected.")
                else:
                    pinfo = game["players"][username]
                    if pinfo.get("connected", True):
                        pinfo["connected"] = False
                        pinfo["disconnected_time"] = time.time()
                        print(f"⚠️ Player {username} in room {room_id} is now disconnected.")
                break

    # ==================== Register & Login ====================
    def register(self, request: Request) -> Response:
        if len(request.args) < 2:
            return Response(None, "Usage: register <username> <password>")

        username, password = request.args[:2]
        new_user = User(username, "N/A", username, Role.USER, password)
        try:
            self.__user_db.add_user(new_user)
            return Response(f"Register success for {username}", None)
        except ValueError as e:
            return Response(None, str(e))

    def login(self, request: Request) -> Response:
        if len(request.args) < 2:
            return Response(None, "Usage: login <username> <password>")

        username, password = request.args[:2]
        duration = timedelta(hours=1)
        try:
            token_obj = self.__auth_service.authenticate(Credentials(username, password), duration)
            return Response({"token": token_obj.signature}, None)
        except ValueError as e:
            return Response(None, str(e))

    def __check_authorization(self, request, required_role: Role = Role.USER):
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
        elif request.name == "leave_room":
            return self.leave_room(request)
        elif request.name == "reconnect":
            return self.reconnect(request)
        else:
            raise ValueError(f"Unknown method: {request.name}")

    # ==================== 创建房间 ====================
    def create_room(self, request):
        room_id = request.args[0]
        if room_id in self.games:
            return Response(None, "Room already exists")

        self.games[room_id] = {
            "players": {},
            "players_order": [],
            "current_turn": None,
            "called_number": None,  # None表示还没开始
            "winner": None
        }
        return Response(f"Room {room_id} created successfully", None)

    # ==================== 加入房间 ====================
    def join_room(self, request):
        """
        若 called_number 不为 None => 游戏已经开始 => 拒绝加入
        """
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]

        # 如果本局游戏已开始 => 拒绝
        if game["called_number"] is not None:
            return Response(None, "无法加入该房间，游戏已经开始。")

        if req_player_name != real_username:
            return Response(None, f"Token mismatch. Must join as {real_username}")
        if req_player_name in game["players"]:
            return Response(None, "Player already in room")

        dice_number = random.randint(1, 6)
        dice_color = random.choice(["red", "yellow", "green", "blue", "black"])
        game["players"][req_player_name] = {
            "dice_number": dice_number,
            "dice_color": dice_color,
            "score": 0,
            "connected": True,
            "disconnected_time": None
        }
        game["players_order"].append(req_player_name)

        if game["current_turn"] is None:
            game["current_turn"] = req_player_name

        return Response(
            f"{req_player_name} joined room {room_id}, dice: {dice_number} {dice_color}",
            None
        )

    # ==================== 喊数 ====================
    def call_number(self, request):
        room_id, req_player_name, number = request.args[:3]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        if game["current_turn"] != req_player_name:
            return Response(None, "Not your turn to call")

        # 若是第一次call => 初始化
        if game["called_number"] is None:
            game["called_number"] = max(3*len(game["players"])+1, 7)

        prev_call = game["called_number"]
        number = int(number)
        if number <= prev_call:
            return Response(None, "Called number must be greater than the previous one")

        game["called_number"] = number

        players = game["players_order"]
        if not players:
            return Response(None, "No players in room")

        i = players.index(req_player_name)
        next_i = (i + 1) % len(players)
        game["current_turn"] = players[next_i]

        return Response(f"{req_player_name} called {number}, next turn: {players[next_i]}", None)

    # ==================== 揭示结果 ====================
    def reveal_result(self, request):
        """
        游戏结束 => 重置房间(发新骰子、清空 called_number, winner, etc.)
        """
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        if req_player_name != real_username:
            return Response(None, f"Token mismatch, must reveal_result as {real_username}")
        if req_player_name != game["current_turn"]:
            return Response(None, f"Only the current turn player ({game['current_turn']}) can reveal the result.")

        if game["called_number"] is None:
            return Response(None, "No call has been made yet.")

        total_sum = sum(p["dice_number"] for p in game["players"].values())
        if game["called_number"] < total_sum:
            result_str = f"{req_player_name} loses! (Called number {game['called_number']} > total dice sum {total_sum})"
        else:
            result_str = f"{req_player_name} wins! (Called number {game['called_number']} <= total dice sum {total_sum})"

        game["winner"] = req_player_name if "wins" in result_str else "UNKNOWN"

        # 重置游戏
        self.reset_game(room_id)

        return Response(result_str, None)

    def reset_game(self, room_id):
        """
        重置 => 新骰子, winner=None, called_number=None, current_turn=players_order[0]
        """
        if room_id not in self.games:
            return
        game = self.games[room_id]

        game["winner"] = None
        game["called_number"] = None

        for uname, pinfo in game["players"].items():
            pinfo["dice_number"] = random.randint(1, 6)
            pinfo["dice_color"] = random.choice(["red", "yellow", "green", "blue", "black"])

        if game["players_order"]:
            game["current_turn"] = game["players_order"][0]
        else:
            game["current_turn"] = None

        print(f"✅ Room {room_id} reset for a new round.")

    # ==================== 获取状态 ====================
    def get_game_state(self, request):
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        room_id = request.args[0]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        self.check_reconnection_timeout(room_id)
        return Response(self.games[room_id], None)

    # ==================== 离开房间 ====================
    def leave_room(self, request):
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        if len(request.args) < 2:
            return Response(None, "Usage: leave_room <room_id> <player_name>")

        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, f"Room {room_id} does not exist")

        game = self.games[room_id]
        if req_player_name != real_username:
            return Response(None, f"Token mismatch, must leave_room as {real_username}")

        if req_player_name not in game["players"]:
            return Response(None, "Player not in this room")

        game_not_started = (game["called_number"] is None)
        game_ended = (game["winner"] is not None)

        if not (game_not_started or game_ended):
            return Response(None, "Cannot leave room; game in progress!")

        del game["players"][req_player_name]
        if req_player_name in game["players_order"]:
            game["players_order"].remove(req_player_name)

        if not game["players"]:
            del self.games[room_id]
            return Response(f"Player {req_player_name} left room {room_id}; room closed (no players).", None)

        return Response(f"Player {req_player_name} left room {room_id} successfully.", None)

    # ==================== 重连 ====================
    def reconnect(self, request):
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        if len(request.args) < 2:
            return Response(None, "Usage: reconnect <room_id> <player_name>")

        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, f"Room {room_id} does not exist")

        if req_player_name != real_username:
            return Response(None, f"Token mismatch, must reconnect as {real_username}")

        game = self.games[room_id]
        if req_player_name not in game["players"]:
            return Response(None, "Player not in this room. Please join instead?")

        player_state = game["players"][req_player_name]
        if player_state.get("connected", True):
            return Response(None, "You are already connected. No need to reconnect.")

        disconnected_time = player_state.get("disconnected_time", None)
        if disconnected_time is None:
            return Response(None, "No disconnected timestamp found. Can't reconnect.")

        if time.time() - disconnected_time > 120:
            return Response(None, "Reconnection time (120s) has expired.")

        player_state["connected"] = True
        player_state["disconnected_time"] = None
        print(f"✅ Player {req_player_name} reconnected to room {room_id}.")

        return Response(f"Reconnection successful for {req_player_name}.", None)

    # ==================== 超时检查 ====================
    def check_reconnection_timeout(self, room_id):
        """
        如果有人超时 => 移除他们
        如果房间里还有人 => 重置游戏 (重新发dice、call=none、winner=none、turn=第一位)
        如果没人 => 删房
        """
        if room_id not in self.games:
            return
        game = self.games[room_id]
        now = time.time()
        to_remove = []

        for username, info in list(game["players"].items()):
            if info.get("connected") == False:
                dtime = info.get("disconnected_time", 0)
                if now - dtime > 120:
                    to_remove.append(username)

        if to_remove:
            print(f"Removing players {to_remove} from room {room_id} for 120s timeout.")
            for user in to_remove:
                del game["players"][user]
                if user in game["players_order"]:
                    game["players_order"].remove(user)

            # 若仍有人在 => 重置游戏
            if game["players"]:
                self.reset_game(room_id)
            else:
                del self.games[room_id]
                print(f"Room {room_id} removed (no players left).")

    def stop(self):
        self.running = False
        self.server_socket.close()


if __name__ == '__main__':
    server = MindRollServer(port=8080)
    print("MindRoll Server: if a player times out => remove them & reset the game; no join if game started. Also reveals => reset.")
    server.start()
