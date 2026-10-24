"""
core/search.py — Các giải thuật tìm kiếm tổng quát.
Người sở hữu: TV1.

Các giải thuật CHỈ gọi hàm của interface Problem (core/problem.py), không
biết gì về luật của Pipes hay Tents. Nhờ vậy cùng một code giải được mọi bài.

  dfs           : Depth-First Search  (blind search)
  bfs           : Breadth-First Search (blind search, tùy chọn để so sánh)
  astar         : A* = Best-First Search với f(n) = g(n) + h(n)
  hill_climbing : Steepest-Ascent Hill Climbing + random restart

Cách tính số liệu (dùng thống nhất cho mọi giải thuật):
  nodes_expanded  : số nút được lấy ra khỏi frontier và xét con
                    (Hill Climbing: số trạng thái đã đứng tại đó và xét láng giềng)
  nodes_generated : số nút con được sinh ra bởi result() / neighbors()
  max_frontier    : số nút lớn nhất cùng lúc nằm trong frontier
                    (Hill Climbing: số láng giềng lớn nhất xét trong một bước)
"""
from __future__ import annotations

import heapq
import itertools
import random
from collections import deque
from typing import Optional

from core.problem import Problem, SearchResult


class Node:
    """Một nút trên cây tìm kiếm. Lưu con trỏ cha thay vì cả đường đi
    để tiết kiệm bộ nhớ; đường đi được dựng lại khi tìm thấy đích."""

    __slots__ = ("state", "parent", "action", "g", "depth")

    def __init__(self, state, parent=None, action=None, g=0.0, depth=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.g = g            # chi phí đường đi từ gốc tới nút này
        self.depth = depth

    def path(self) -> list:
        actions, node = [], self
        while node.parent is not None:
            actions.append(node.action)
            node = node.parent
        actions.reverse()
        return actions


# ----------------------------------------------------------------------
# DFS
# ----------------------------------------------------------------------
def dfs(problem: Problem, tracer=None, check_visited: bool = True) -> SearchResult:
    """Depth-First Search dùng stack (LIFO).

    is_valid() được gọi NGAY SAU khi sinh nút con: nút con vi phạm ràng buộc
    bị loại, không đưa vào stack (cắt nhánh sớm).

    check_visited=True: không đưa lại vào stack trạng thái đã gặp, tránh lặp
    vô hạn khi không gian trạng thái có chu trình. Nếu cách mô hình hóa đảm
    bảo không có trạng thái lặp (gán lần lượt từng ô), có thể đặt False để
    tiết kiệm bộ nhớ.
    """
    start = problem.initial_state()
    if not problem.is_valid(start):
        return SearchResult("dfs", False, note="Trạng thái đầu không hợp lệ")

    stack = [Node(start)]
    visited = {start} if check_visited else None
    expanded = generated = 0
    max_frontier = 1

    while stack:
        node = stack.pop()
        expanded += 1
        if tracer is not None:
            tracer.log(problem, node.state, len(stack), "expand", node.depth)

        if problem.goal_test(node.state):
            return SearchResult("dfs", True, node.state, node.path(),
                                expanded, generated, max_frontier)

        children = []
        for action in problem.actions(node.state):
            child_state = problem.result(node.state, action)
            generated += 1
            if not problem.is_valid(child_state):
                continue
            if visited is not None:
                if child_state in visited:
                    continue
                visited.add(child_state)
            g = node.g + problem.step_cost(node.state, action)
            children.append(Node(child_state, node, action, g, node.depth + 1))

        # Đảo ngược để hành động đầu tiên trong actions() được duyệt trước.
        stack.extend(reversed(children))
        if len(stack) > max_frontier:
            max_frontier = len(stack)

    return SearchResult("dfs", False, None, [], expanded, generated, max_frontier,
                        note="Đã duyệt hết không gian trạng thái")


# ----------------------------------------------------------------------
# BrFS (tùy chọn, để so sánh bộ nhớ với DFS trên input nhỏ)
# ----------------------------------------------------------------------
def bfs(problem: Problem, tracer=None) -> SearchResult:
    """Breadth-First Search dùng hàng đợi (FIFO)."""
    start = problem.initial_state()
    if not problem.is_valid(start):
        return SearchResult("bfs", False, note="Trạng thái đầu không hợp lệ")

    queue = deque([Node(start)])
    visited = {start}
    expanded = generated = 0
    max_frontier = 1

    while queue:
        node = queue.popleft()
        expanded += 1
        if tracer is not None:
            tracer.log(problem, node.state, len(queue), "expand", node.depth)

        if problem.goal_test(node.state):
            return SearchResult("bfs", True, node.state, node.path(),
                                expanded, generated, max_frontier)

        for action in problem.actions(node.state):
            child_state = problem.result(node.state, action)
            generated += 1
            if not problem.is_valid(child_state) or child_state in visited:
                continue
            visited.add(child_state)
            g = node.g + problem.step_cost(node.state, action)
            queue.append(Node(child_state, node, action, g, node.depth + 1))

        if len(queue) > max_frontier:
            max_frontier = len(queue)

    return SearchResult("bfs", False, None, [], expanded, generated, max_frontier,
                        note="Đã duyệt hết không gian trạng thái")


# ----------------------------------------------------------------------
# A*
# ----------------------------------------------------------------------
def astar(problem: Problem, tracer=None) -> SearchResult:
    """A*: Best-First Search chọn nút có f(n) = g(n) + h(n) nhỏ nhất.

    Hàng đợi ưu tiên chứa (f, -g, counter, node):
      - f nhỏ hơn được chọn trước;
      - khi f bằng nhau, ưu tiên g LỚN hơn (nút sâu hơn). Với các puzzle mà
        mọi lời giải nằm cùng độ sâu, cách phá hòa này giúp A* đi sâu nhanh;
      - counter tăng dần để không bao giờ phải so sánh hai Node với nhau.
    closed: tập trạng thái đã mở rộng, không mở rộng lại.
    """
    start = problem.initial_state()
    if not problem.is_valid(start):
        return SearchResult("astar", False, note="Trạng thái đầu không hợp lệ")

    counter = itertools.count()
    root = Node(start)
    frontier = [(problem.h(start), 0.0, next(counter), root)]
    best_g = {start: 0.0}
    closed = set()
    expanded = generated = 0
    max_frontier = 1

    while frontier:
        _, _, _, node = heapq.heappop(frontier)
        if node.state in closed:
            continue          # bản cũ hơn của trạng thái đã được mở rộng
        closed.add(node.state)
        expanded += 1
        if tracer is not None:
            tracer.log(problem, node.state, len(frontier), "expand", node.depth)

        if problem.goal_test(node.state):
            return SearchResult("astar", True, node.state, node.path(),
                                expanded, generated, max_frontier)

        for action in problem.actions(node.state):
            child_state = problem.result(node.state, action)
            generated += 1
            if not problem.is_valid(child_state) or child_state in closed:
                continue
            g = node.g + problem.step_cost(node.state, action)
            if g < best_g.get(child_state, float("inf")):
                best_g[child_state] = g
                child = Node(child_state, node, action, g, node.depth + 1)
                f = g + problem.h(child_state)
                heapq.heappush(frontier, (f, -g, next(counter), child))

        if len(frontier) > max_frontier:
            max_frontier = len(frontier)

    return SearchResult("astar", False, None, [], expanded, generated, max_frontier,
                        note="Đã duyệt hết không gian trạng thái")


# ----------------------------------------------------------------------
# Hill Climbing
# ----------------------------------------------------------------------
def hill_climbing(problem: Problem, tracer=None, restarts: int = 20,
                  max_steps: int = 10_000, sideways: int = 0,
                  seed: int = 0) -> SearchResult:
    """Steepest-Ascent Hill Climbing với random restart.

    Mỗi bước xét TOÀN BỘ láng giềng, chọn láng giềng có h nhỏ nhất
    (nếu nhiều láng giềng cùng h nhỏ nhất thì chọn ngẫu nhiên một cái).
      - h giảm            : chuyển sang láng giềng đó.
      - h không đổi       : chỉ chuyển nếu còn lượt đi ngang (sideways).
      - không có láng giềng tốt hơn: kẹt ở cực tiểu địa phương hoặc vùng
        bằng phẳng -> random restart từ problem.random_state().

    restarts : số lần bắt đầu lại tối đa (tổng số lần thử = restarts + 1)
    sideways : số bước đi ngang tối đa liên tiếp (0 = Hill Climbing thuần)
    seed     : hạt giống ngẫu nhiên, cố định để kết quả lặp lại được
    """
    rng = random.Random(seed)
    expanded = generated = 0
    max_frontier = 0
    best_state, best_h = None, float("inf")

    for attempt in range(restarts + 1):
        current = problem.random_state(rng)
        current_h = problem.h(current)
        side_moves = 0
        if tracer is not None:
            tracer.log(problem, current, 0, "restart" if attempt else "move", 0)

        for step in range(max_steps):
            expanded += 1
            if problem.goal_test(current):
                return SearchResult("hc", True, current, [], expanded, generated,
                                    max_frontier, restarts=attempt)

            nbrs = problem.neighbors(current)
            generated += len(nbrs)
            if len(nbrs) > max_frontier:
                max_frontier = len(nbrs)
            if not nbrs:
                break

            scored = [(problem.h(s), s) for s in nbrs]
            min_h = min(hv for hv, _ in scored)
            best = [s for hv, s in scored if hv == min_h]
            nxt = best[0] if len(best) == 1 else rng.choice(best)

            if min_h < current_h:
                side_moves = 0
            elif min_h == current_h and side_moves < sideways:
                side_moves += 1
            else:
                break   # cực tiểu địa phương / vùng bằng phẳng

            current, current_h = nxt, min_h
            if tracer is not None:
                tracer.log(problem, current, len(nbrs), "move", step + 1)

        if current_h < best_h:
            best_state, best_h = current, current_h

    return SearchResult("hc", False, None, [], expanded, generated, max_frontier,
                        restarts=restarts,
                        note=f"Kẹt ở cực tiểu địa phương sau {restarts} lần restart; "
                             f"h tốt nhất đạt được = {best_h}")


ALGORITHMS = {
    "dfs": dfs,
    "bfs": bfs,
    "astar": astar,
    "hc": hill_climbing,
}


def run(algo: str, problem: Problem, tracer=None, **kwargs) -> SearchResult:
    """Gọi giải thuật theo tên: "dfs", "bfs", "astar", "hc"."""
    if algo not in ALGORITHMS:
        raise ValueError(f"Không có giải thuật '{algo}'. Chọn một trong {list(ALGORITHMS)}")
    fn = ALGORITHMS[algo]
    if algo != "hc":
        kwargs.pop("restarts", None)
        kwargs.pop("seed", None)
        kwargs.pop("sideways", None)
    return fn(problem, tracer=tracer, **kwargs)
