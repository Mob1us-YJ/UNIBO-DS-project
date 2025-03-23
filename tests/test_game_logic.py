import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.server.game_logic import GameRoom

class TestGameLogic(unittest.TestCase):
    def test_add_player(self):
        room = GameRoom("room1")
        room.add_player("player1")
        self.assertIn("player1", room.players)

    def test_call_number(self):
        room = GameRoom("room1")
        room.add_player("player1")
        room.add_player("player2")
        room.call_number("player1", 10)
        self.assertEqual(room.called_number, 10)

    def test_reveal_result(self):
        room = GameRoom("room1")
        room.add_player("player1")
        room.add_player("player2")
        # 确保 player1 是当前轮到的玩家
        room.current_turn = "player1"
        # 调用 reveal_result
        result = room.reveal_result("player1")
        self.assertIn("result_str", result)

    def test_remove_player(self):
        room = GameRoom("room1")
        room.add_player("player1")
        room.remove_player("player1")
        self.assertNotIn("player1", room.players)