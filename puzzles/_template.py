"""
puzzles/_template.py — FILE MẪU cho TV2 (Pipes) và TV3 (Tents).

Cách dùng:
    TV2: chép file này thành puzzles/pipes.py, đổi tên lớp thành Pipes.
    TV3: chép file này thành puzzles/tents.py, đổi tên lớp thành Tents.
Xem ví dụ đã cài đầy đủ ở examples/nqueens.py.

Ba quy ước bắt buộc (chi tiết ở core/problem.py):
    1. state là tuple (hashable), không dùng list.
    2. result() trả về state MỚI, không sửa state cũ.
    3. encode() trả về list các list (str/int) để GUI vẽ.

Kiểm tra nhanh sau khi cài:
    python main.py --puzzle pipes --algo dfs --input inputs/pipes/01.txt
"""
from __future__ import annotations

import random

from core.problem import Problem


class MyPuzzle(Problem):
    name = "my_puzzle"          # đổi thành "pipes" hoặc "tents"

    def __init__(self, grid, **clues):
        self.grid = grid        # dữ liệu đọc từ file input
        self.clues = clues      # ví dụ Tents: số lều mỗi hàng/cột

    # ---------- DFS / A* ----------
    def initial_state(self):
        raise NotImplementedError

    def actions(self, state):
        raise NotImplementedError

    def result(self, state, action):
        raise NotImplementedError

    def is_valid(self, state) -> bool:
        raise NotImplementedError

    def goal_test(self, state) -> bool:
        raise NotImplementedError

    # ---------- Heuristic ----------
    def h(self, state) -> float:
        raise NotImplementedError

    # ---------- Hill Climbing (TV2 bắt buộc; TV3 không cần) ----------
    def random_state(self, rng: random.Random):
        raise NotImplementedError

    def neighbors(self, state):
        raise NotImplementedError

    # ---------- GUI ----------
    def encode(self, state):
        raise NotImplementedError

    def size_label(self) -> str:
        return ""


def load_problem(path: str) -> MyPuzzle:
    """Đọc file input, trả về đối tượng bài toán. BẮT BUỘC phải có hàm này."""
    raise NotImplementedError
