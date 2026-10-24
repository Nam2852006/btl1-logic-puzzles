"""gui/make_demo_traces.py - Sinh trace GIẢ cho Pipes và Tents để thử GUI khi chưa có dữ liệu thật.
Người sở hữu: TV4.

Dữ liệu ở đây KHÔNG phải kết quả của giải thuật thật, chỉ theo đúng định dạng trace và quy ước
encode() mô tả ở đầu gui/render_pipes.py và gui/render_tents.py. Khi TV2, TV3 có bài thật thì
dùng trace thật (python main.py ... --trace) thay cho các file này.

    python gui/make_demo_traces.py      # ghi vào gui/demo_traces/
"""
from __future__ import annotations

import json
import os
import random

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_traces")
DIRS = {"N": (-1, 0, "S"), "E": (0, 1, "W"), "S": (1, 0, "N"), "W": (0, -1, "E")}
ROT = {"N": "E", "E": "S", "S": "W", "W": "N"}


def write(name, meta, steps, result):
    os.makedirs(OUT, exist_ok=True)
    meta = {"type": "meta", **meta, "total_steps": len(steps), "recorded_steps": len(steps),
            "truncated": False}
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
        for s in steps:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- Pipes
def pipes_solution(n, rng):
    """Cây khung ngẫu nhiên trên lưới n x n: mọi ô nối liền, không có vòng."""
    sides = [[set() for _ in range(n)] for _ in range(n)]
    seen, stack = {(0, 0)}, [(0, 0)]
    while stack:
        r, c = stack[-1]
        nxt = [(d, r + dr, c + dc, back) for d, (dr, dc, back) in DIRS.items()
               if 0 <= r + dr < n and 0 <= c + dc < n and (r + dr, c + dc) not in seen]
        if not nxt:
            stack.pop()
            continue
        d, nr, nc, back = rng.choice(nxt)
        sides[r][c].add(d)
        sides[nr][nc].add(back)
        seen.add((nr, nc))
        stack.append((nr, nc))
    return [["".join(x for x in "NESW" if x in s) for s in row] for row in sides]


def rotate(cell):
    return "".join(x for x in "NESW" if any(ROT[y] == x for y in cell))


def dangling(grid):
    n, bad = len(grid), 0
    for r in range(n):
        for c in range(n):
            for d in grid[r][c]:
                dr, dc, back = DIRS[d]
                nr, nc = r + dr, c + dc
                if not (0 <= nr < n and 0 <= nc < n) or back not in grid[nr][nc]:
                    bad += 1
    return bad


def make_pipes(n=5):
    rng = random.Random(1)
    sol = pipes_solution(n, rng)
    meta = {"puzzle": "pipes", "input": "inputs/pipes/demo.txt", "size": f"{n}x{n}"}

    # DFS giả: gán lần lượt từng ô theo hàng, ô chưa gán là "?"
    cur = [["?"] * n for _ in range(n)]
    steps = [{"type": "step", "step": 1, "event": "expand", "grid": [r[:] for r in cur],
              "h": n * n, "frontier": 0, "depth": 0}]
    for k in range(n * n):
        r, c = divmod(k, n)
        cur[r][c] = sol[r][c]
        steps.append({"type": "step", "step": k + 2, "event": "expand", "grid": [row[:] for row in cur],
                      "h": n * n - k - 1, "frontier": 3 - k % 3, "depth": k + 1})
    write("pipes_dfs_demo.jsonl", {**meta, "algorithm": "dfs"}, steps,
          {"type": "result", "success": True, "grid": sol, "nodes_expanded": len(steps), "restarts": 0})

    # Hill Climbing giả: xoay từng ô sai về đúng, có một lần restart ở giữa
    steps, step = [], 0

    def scramble():
        return [[sol[r][c] if rng.random() < 0.3 else _rot_n(sol[r][c], rng.randint(1, 3))
                 for c in range(n)] for r in range(n)]

    def log(event, g):
        nonlocal step
        step += 1
        steps.append({"type": "step", "step": step, "event": event, "grid": [row[:] for row in g],
                      "h": dangling(g), "frontier": n * n * 3, "depth": 0})

    g = scramble()
    log("move", g)
    wrong = [(r, c) for r in range(n) for c in range(n) if g[r][c] != sol[r][c]]
    for r, c in wrong[: len(wrong) // 2]:
        g[r][c] = sol[r][c]
        log("move", g)
    g = scramble()
    log("restart", g)
    wrong = [(r, c) for r in range(n) for c in range(n) if g[r][c] != sol[r][c]]
    for r, c in wrong:
        g[r][c] = sol[r][c]
        log("move", g)
    write("pipes_hc_demo.jsonl", {**meta, "algorithm": "hc"}, steps,
          {"type": "result", "success": True, "grid": sol, "nodes_expanded": step, "restarts": 1})


def _rot_n(cell, k):
    for _ in range(k):
        cell = rotate(cell)
    return cell


# ---------------------------------------------------------------- Tents
def make_tents(n=6):
    rng = random.Random(7)
    tents, trees, taken = [], [], set()
    cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(cells)
    for r, c in cells:
        if len(tents) >= 7:
            break
        if any(abs(r - a) <= 1 and abs(c - b) <= 1 for a, b in tents) or (r, c) in taken:
            continue
        for dr, dc in rng.sample([(-1, 0), (1, 0), (0, -1), (0, 1)], 4):
            t = (r + dr, c + dc)
            if 0 <= t[0] < n and 0 <= t[1] < n and t not in taken and t not in tents:
                tents.append((r, c))
                trees.append(t)
                taken.update({(r, c), t})
                break
    rows = [sum(1 for t in tents if t[0] == r) for r in range(n)]
    cols = [sum(1 for t in tents if t[1] == c) for c in range(n)]

    def grid(placed, extra=()):
        g = [["."] * n + [rows[r]] for r in range(n)]
        for tr, tc in trees:
            g[tr][tc] = "T"
        for r, c in list(placed) + list(extra):
            g[r][c] = "^"
        return g + [cols + [""]]

    meta = {"puzzle": "tents", "input": "inputs/tents/demo.txt", "size": f"{n}x{n}"}

    def steps_for(algo):
        steps, placed, k = [], [], 0

        def log(event, g, h, frontier):
            nonlocal k
            k += 1
            steps.append({"type": "step", "step": k, "event": event, "grid": g, "h": h,
                          "frontier": frontier, "depth": len(placed)})

        log("expand", grid(placed), len(trees), 0)
        for i, t in enumerate(tents):
            if i == 2:       # thử đặt sai (lều chạm lều) rồi quay lui
                bad = (tents[1][0] + 1, tents[1][1] + 1)
                if 0 <= bad[0] < n and 0 <= bad[1] < n and bad not in trees and bad not in tents:
                    log("expand", grid(placed, [bad]), len(trees) - len(placed) - 1, 4 + i)
            placed.append(t)
            log("expand", grid(placed), len(trees) - len(placed), 2 + i)
        return steps

    for algo in ("dfs", "astar"):
        steps = steps_for(algo)
        write(f"tents_{algo}_demo.jsonl", {**meta, "algorithm": algo}, steps,
              {"type": "result", "success": True, "grid": grid(tents), "nodes_expanded": len(steps),
               "restarts": 0})


if __name__ == "__main__":
    make_pipes()
    make_tents()
    print("Đã ghi trace giả vào", OUT)
