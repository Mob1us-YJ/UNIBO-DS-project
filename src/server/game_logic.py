# src/server/game_logic.py
import random
import time

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}  # { username: {dice_number, dice_color, score, connected, disconnected_time } }
        self.players_order = []  # 玩家加入顺序
        self.current_turn = None  # 当前回合的玩家
        self.called_number = None  # 当前叫数
        self.winner = None  # 获胜者

    def add_player(self, player_name):
        """添加玩家到房间"""
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
        """玩家叫数"""
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to start the game")

        if self.current_turn != player_name:
            raise ValueError("Not your turn to call")

        # 若是第一次call => 初始化
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
        """揭示结果"""
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to start the game")
        if self.current_turn != player_name:
            raise ValueError("Not your turn to reveal")

        if self.called_number is None:
            raise ValueError("No call has been made yet.")

        total_sum = sum(p["dice_number"] for p in self.players.values())
        if self.called_number < total_sum:
            result_str = f"{player_name} loses! (Called number {self.called_number} > total dice sum {total_sum})"
            self.winner = "UNKNOWN"
            self.players[player_name]["score"] -= 1
        else:
            result_str = f"{player_name} wins! (Called number {self.called_number} <= total dice sum {total_sum})"
            self.winner = player_name
            self.players[player_name]["score"] += 1

        # 重置游戏
        self.reset_game()

         # 返回所有玩家的分数和骰子信息
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
        """重置游戏状态"""
        self.winner = None
        self.called_number = None

        for player_info in self.players.values():
            player_info["dice_number"] = random.randint(1, 6)
            player_info["dice_color"] = random.choice(["red", "yellow", "green", "blue", "black"])

        if self.players_order:
            self.current_turn = self.players_order[0]
        else:
            self.current_turn = None

    def remove_player(self, player_name):
        """移除玩家"""
        if player_name not in self.players:
            raise ValueError("Player not in room")

        del self.players[player_name]
        if player_name in self.players_order:
            self.players_order.remove(player_name)

        if not self.players:
            return True  # 房间为空，需要删除
        return False

    def check_reconnection_timeout(self):
        """检查玩家是否超时"""
        now = time.time()
        to_remove = []

        for username, info in list(self.players.items()):
            if info.get("connected") == False:
                dtime = info.get("disconnected_time", 0)
                if now - dtime > 120:
                    to_remove.append(username)

        for user in to_remove:
            self.remove_player(user)

        return to_remove