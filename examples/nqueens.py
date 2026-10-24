"""
examples/nqueens.py — Bài toán đồ chơi N-Queens để TV1 test giải thuật
trước khi Pipes và Tents xong. KHÔNG phải một trong 2 bài nộp.

Đây cũng là ví dụ mẫu cho TV2, TV3 về cách cài một Problem.

Biểu diễn trạng thái (dùng chung cho DFS, A* và Hill Climbing):
    tuple độ dài N, phần tử thứ r = cột của quân hậu ở hàng r,
    None nếu hàng r chưa đặt hậu.
    Ví dụ N=4: (1, 3, None, None) = đã đặt hậu ở hàng 0 cột 1, hàng 1 cột 3.

File input: một dòng chứa N (dòng bắt đầu bằng # là chú thích).
"""
from __future__ import annotations

import random
from typing import List

from core.problem import Problem


class NQueens(Problem):
    name = "nqueens"

    def __init__(self, n: int):
        self.n = n

    # ---------------- DFS / A* ----------------
    def initial_state(self):
        return (None,) * self.n

    def actions(self, state) -> List[int]:
        # Đặt hậu vào hàng trống đầu tiên; hành động = chọn cột.
        if None not in state:
            return []
        return list(range(self.n))

    def result(self, state, action):
        row = state.index(None)
        return state[:row] + (action,) + state[row + 1:]   # tuple MỚI

    def is_valid(self, state) -> bool:
        return self._attacking_pairs(state) == 0

    def goal_test(self, state) -> bool:
        return None not in state and self._attacking_pairs(state) == 0

    # ---------------- Heuristic ----------------
    def h(self, state) -> float:
        # Số hàng chưa đặt + số cặp hậu ăn nhau.
        # Với trạng thái đầy đủ (Hill Climbing): chỉ còn số cặp ăn nhau.
        # Với trạng thái dở dang hợp lệ (A*): h = số hậu còn phải đặt, nên
        # f = g + h là hằng số -> A* thoái hóa như mục 2 tài liệu phân công
        # đã cảnh báo. Pipes/Tents cần h có thông tin hơn.
        return state.count(None) + self._attacking_pairs(state)

    # ---------------- Hill Climbing ----------------
    def random_state(self, rng: random.Random):
        return tuple(rng.randrange(self.n) for _ in range(self.n))

    def neighbors(self, state):
        result = []
        for row in range(self.n):
            for col in range(self.n):
                if col != state[row]:
                    result.append(state[:row] + (col,) + state[row + 1:])
        return result

    # ---------------- GUI ----------------
    def encode(self, state):
        return [["Q" if state[r] == c else "." for c in range(self.n)]
                for r in range(self.n)]

    def size_label(self) -> str:
        return f"{self.n}x{self.n}"

    # ---------------- Hàm phụ ----------------
    @staticmethod
    def _attacking_pairs(state) -> int:
        placed = [(r, c) for r, c in enumerate(state) if c is not None]
        count = 0
        for i in range(len(placed)):
            r1, c1 = placed[i]
            for j in range(i + 1, len(placed)):
                r2, c2 = placed[j]
                if c1 == c2 or abs(c1 - c2) == abs(r1 - r2):
                    count += 1
        return count


def load_problem(path: str) -> NQueens:
    with open(path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    return NQueens(int(lines[0]))
