# src/server/game_logic.py

import random
import time

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}       # { username: {dice_number, dice_color, score, connected, disconnected_time } }
        self.players_order = [] 
        self.current_turn = None
        self.called_number = None
        self.winner = None

        self.last_result_str = None   # save the last result string
        self.last_result_time = None    # save the last result time

    def add_player(self, player_name):
        # Deny joining if game has already started
        if self.called_number is not None:
            raise ValueError("Game already started, cannot join room.")
        if player_name in self.players:
            raise ValueError("Player already in room")

        dice_number = random.randint(1, 6)
        dice_color = random.choice(["red", "yellow", "green", "blue", "black"])
        self.players[player_name] = {
            "dice_number": dice_number,
            "dice_color": dice_color,
            "score": 0,
            "connected": True,
            "disconnected_time": None
        }
        self.players_order.append(player_name)

        if self.current_turn is None:
            self.current_turn = player_name

    def call_number(self, player_name, number):
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to start the game")
        if self.current_turn != player_name:
            raise ValueError("Not your turn to call")

        # initial call number
        if self.called_number is None:
            self.called_number = max(3 * len(self.players) + 1, 7)

        number = int(number)
        if number <= self.called_number:
            raise ValueError("Called number must be greater than the previous one")

        self.called_number = number

        # update current turn
        if self.players_order:
            i = self.players_order.index(player_name)
            next_i = (i + 1) % len(self.players_order)
            self.current_turn = self.players_order[next_i]

    def reveal_result(self, player_name):
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to start the game")
        if self.current_turn != player_name:
            raise ValueError("Not your turn to reveal")
        if self.called_number is None:
            raise ValueError("No call has been made yet.")

        total_sum = sum(p["dice_number"] for p in self.players.values())
        if self.called_number < total_sum:
            result_str = f"{player_name} loses! (Called number {self.called_number} > total dice sum {total_sum})"
            self.winner = "DRAW"
            self.players[player_name]["score"] -= 1
        else:
            result_str = f"{player_name} wins! (Called number {self.called_number} <= total dice sum {total_sum})"
            self.winner = player_name
            self.players[player_name]["score"] += 1

        # sacve the result string and time
        self.last_result_str = result_str
        self.last_result_time = time.time()

        # reset the game
        self.reset_game()

        result_info = {
            "result_str": result_str,
            "players": self.players,
            "players_order": self.players_order,
            "current_turn": self.current_turn,
            "called_number": self.called_number,
            "winner": self.winner
        }
        return result_info

    def reset_game(self):
        # remove disconnected players
        for username in list(self.players.keys()):
            if not self.players[username].get("connected", True):
                self.remove_player(username)

        # reset dice
        self.winner = None
        self.called_number = None

        for pinfo in self.players.values():
            pinfo["dice_number"] = random.randint(1, 6)
            pinfo["dice_color"] = random.choice(["red", "yellow", "green", "blue", "black"])
            pinfo["connected"] = True
            pinfo["disconnected_time"] = None

        # reset order
        if self.players_order:
            self.players_order = [uname for uname in self.players_order if uname in self.players]
            self.current_turn = self.players_order[0] if self.players_order else None
        else:
            self.current_turn = None


    def maybe_clear_result(self):
        """
        clear the last result string and time after 3 seconds
        """
        if self.last_result_str and self.last_result_time:
            now = time.time()
            threshold = 3 if self.last_result_str == "Game drawn due to disconnect timeout." else 5
            if now - self.last_result_time > threshold:
                self.reset_game()
                self.last_result_str = None
                self.last_result_time = None

    def remove_player(self, player_name):
        if player_name not in self.players:
            raise ValueError("Player not in room")
        del self.players[player_name]
        if player_name in self.players_order:
            self.players_order.remove(player_name)
        if not self.players:
            return True
        return False

    def check_reconnection_timeout(self):
        """
        check if any player has disconnected for more than 60 seconds.
        """
        now = time.time()
        timeout_occurred = False
        for username, info in self.players.items():
            if not info.get("connected", True):
                dtime = info.get("disconnected_time", 0)
                if now - dtime > 60:
                    timeout_occurred = True
                    break
        if timeout_occurred:
            if not self.last_result_str:
                self.last_result_str = "Game drawn due to disconnect timeout."
                self.last_result_time = time.time()

