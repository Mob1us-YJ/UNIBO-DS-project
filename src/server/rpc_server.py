# src/server/rpc_server.py

import socket
import threading
import json
import traceback
import time
from datetime import datetime, timedelta

from src.common.utils import Request, Response, serialize, deserialize
from src.common.users.mongo_user_service import MongoUserService
from src.common.users.mongo_auth_service import MongoAuthenticationService
from src.common.users import Role, Token, Credentials, User
from src.server.game_logic import GameRoom
from src.server.backup_server import BackupServer

class MindRollServer:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        self.games = {}
        self.backup_server = None

        self.__user_db = MongoUserService()
        self.__auth_service = MongoAuthenticationService(self.__user_db)

        # { room_id: GameRoom(...) }
        self.games = {}

    def set_backup_server(self, backup_server):
         """Set the backup server for this server."""
         self.backup_server = backup_server

    def sync_data(self):
         """Sync game data with the backup server."""
         if self.backup_server:
            self.backup_server.update_games(self.games)

    def update_games(self, games):
        """Update the game data from the backup server."""
        self.games = games

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

                # Check if token is present in metadata
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
            if user_token_str:
                self.mark_player_disconnected(user_token_str)
            client_socket.close()

    def send_response(self, client_socket, response_obj):
        serialized = serialize(response_obj)
        client_socket.sendall(serialized.encode('utf-8'))

    def mark_player_disconnected(self, token_str):
        token_obj = self.__auth_service.validate_token_by_str(token_str)
        if not token_obj:
            return
        username = token_obj.user.username

        for room_id, game in list(self.games.items()):
            if username in game.players:
                if len(game.players) == 1:
                    del self.games[room_id]
                    print(f"Room {room_id} removed (only player {username} disconnected).")
                else:
                    pinfo = game.players[username]
                    if pinfo.get("connected", True):
                        pinfo["connected"] = False
                        pinfo["disconnected_time"] = time.time()
                        print(f"⚠️ Player {username} in room {room_id} is now disconnected.")
                break

    # ============= Register & Login ============
    def register(self, request: Request) -> Response:
        if len(request.args) < 2:
            return Response(None, "Usage: register <username> <password>")

        username, password = request.args[:2]
        new_user = User(username, username, Role.USER, password)
        if self.__user_db.get_user_by_username(username):
                return Response(None, "Username already exists")
        try:
            self.__user_db.add_user(new_user)
            return Response(f"Register success for {username}", None)
        except Exception as e:
            return Response(None, f"Registration failed: {e}")


    def login(self, request: Request) -> Response:
        if len(request.args) < 2:
            return Response(None, "Usage: login <username> <password>")

        username, password = request.args[:2]
        try:
            token_obj = self.__auth_service.authenticate(Credentials(username, password))
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

    # ============== Game Logic Calls ============
    def create_room(self, request):
        room_id = request.args[0]
        if room_id in self.games:
            return Response(None, "Room already exists")
        self.games[room_id] = GameRoom(room_id)
        self.sync_data()
        return Response(f"Room {room_id} created successfully", None)

    def join_room(self, request):
        token_obj = self.__check_authorization(request)
        real_username = token_obj.user.username

        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, "Room does not exist")
        game = self.games[room_id]
        if game.called_number is not None:
            return Response(None, "Game Started, can't join")
        try:
            game.add_player(req_player_name)
            self.sync_data()
            return Response(f"{req_player_name} joined room {room_id}", None)
        except ValueError as e:
            return Response(None, str(e))

    def call_number(self, request):
        room_id, req_player_name, number = request.args[:3]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        try:
            game.call_number(req_player_name, number)
            self.sync_data()
            return Response(f"{req_player_name} called {number}, next turn: {game.current_turn}", None)
        except ValueError as e:
            return Response(None, str(e))

    def reveal_result(self, request):
        """
        "Reveal” => game.reveal_result() =>  current_turn = None, last_result_str = "xxx" =>
        others get_game_state --> game.last_result_str + new dice
        """
        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        try:
            result_info = game.reveal_result(req_player_name)
            self.sync_data()
            return Response(result_info, None)
        except ValueError as e:
            return Response(None, str(e))

    def get_game_state(self, request):
        room_id = request.args[0]
        if room_id not in self.games:
            return Response(None, "Room does not exist")
        game = self.games[room_id]
        game.check_reconnection_timeout()  # check if any player reconnected after 60s
        game.maybe_clear_result()          # check game result after 3s or 5s

        game_state = {
            "players": game.players,
            "players_order": game.players_order,
            "current_turn": game.current_turn,
            "called_number": game.called_number,
            "winner": game.winner,
            "last_result_str": game.last_result_str
        }
        return Response(game_state, None)


    def leave_room(self, request):
        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        try:
            emptied = game.remove_player(req_player_name)
            if emptied:
                del self.games[room_id]
                return Response(f"Player {req_player_name} left room {room_id}; room closed (no players).", None)
            return Response(f"Player {req_player_name} left room {room_id} successfully.", None)
        except ValueError as e:
            return Response(None, str(e))

    def reconnect(self, request):
        room_id, req_player_name = request.args[:2]
        if room_id not in self.games:
            return Response(None, "Room does not exist")

        game = self.games[room_id]
        if req_player_name not in game.players:
            return Response(None, "Player not in this room. Please join instead?")

        player_state = game.players[req_player_name]
        if player_state.get("connected", True):
            return Response(None, "You are already connected. No need to reconnect.")

        disconnected_time = player_state.get("disconnected_time", None)
        if disconnected_time is None:
            return Response(None, "No disconnected timestamp found. Can't reconnect.")

        if time.time() - disconnected_time > 120:
            return Response(None, "Reconnection time (120s) has expired.")

        player_state["connected"] = True
        player_state["disconnected_time"] = None
        return Response(f"Reconnection successful for {req_player_name}.", None)

    def stop(self):
        self.running = False
        self.server_socket.close()

if __name__ == '__main__':
    server = MindRollServer(port=8080)
    print("MindRoll Server with 'pull-style' game state for reveal_result -> all players see same info next poll.")
    server.start()
