# src/server/game_logic.py

import random
import time

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}       # { username: {dice_number, dice_color, score, connected, disconnected_time } }
        self.players_order = [] # 玩家加入顺序
        self.current_turn = None
        self.called_number = None
        self.winner = None

        self.last_result_str = None   # 用于存储上一局的胜负或流局信息
        self.last_result_time = None    # 记录上一局结果产生的时间

    def add_player(self, player_name):
        # 如果游戏已开始（叫数不为 None），则拒绝加入
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

        # 若是第一次 call，则初始化叫数
        if self.called_number is None:
            self.called_number = max(3 * len(self.players) + 1, 7)

        number = int(number)
        if number <= self.called_number:
            raise ValueError("Called number must be greater than the previous one")

        self.called_number = number

        # 更新下一个玩家
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

        # 记录结果及时间
        self.last_result_str = result_str
        self.last_result_time = time.time()

        # 重置游戏状态（在 reveal_result 中立即重置新局）
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
        # 移除所有已掉线的玩家
        for username in list(self.players.keys()):
            if not self.players[username].get("connected", True):
                self.remove_player(username)

        # 重置游戏状态并为剩余玩家分配新骰子
        self.winner = None
        self.called_number = None

        for pinfo in self.players.values():
            pinfo["dice_number"] = random.randint(1, 6)
            pinfo["dice_color"] = random.choice(["red", "yellow", "green", "blue", "black"])
            # 将剩余玩家状态重置为已连接
            pinfo["connected"] = True
            pinfo["disconnected_time"] = None

        # 重置当前轮到玩家为 players_order[0]
        if self.players_order:
            # 同时也需要更新 players_order，移除已掉线的玩家
            self.players_order = [uname for uname in self.players_order if uname in self.players]
            self.current_turn = self.players_order[0] if self.players_order else None
        else:
            self.current_turn = None


    def maybe_clear_result(self):
        """
        如果上次结果产生已超过规定时间，则清空 last_result_str，
        并调用 reset_game() 确保新局开始。
        对于流局信息("Game drawn due to disconnect timeout.")，阈值为3秒，
        对于其他结果，阈值为5秒。
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
        检查断线玩家是否超时120秒。
        如果发现有玩家超时，则将本局游戏判定为流局，
        设置 last_result_str 为流局信息，并记录时间，
        之后由 maybe_clear_result 在3秒后清空结果并重置游戏。
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
            # 不直接调用 reset_game()，等待 maybe_clear_result() 3秒后自动清空

