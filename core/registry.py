"""
core/registry.py — Danh sách bài toán và cặp giải thuật của nhóm.
Người sở hữu: TV1.

Mỗi module bài toán PHẢI có hàm:
    load_problem(path: str, **kw) -> Problem
đọc file input và trả về một đối tượng Problem. kw là tham số tùy chọn của
bài toán (ví dụ Tents: h_mode="naive"), chỉ dùng khi chạy so sánh biến thể.
"""
from __future__ import annotations

import importlib

# Tên bài toán -> module chứa hàm load_problem(path)
PUZZLES = {
    "pipes": "puzzles.pipes",        # TV2
    "tents": "puzzles.tents",        # TV3
    "nqueens": "examples.nqueens",   # TV1, bài đồ chơi để test giải thuật
}

# Cặp giải thuật chạy trong benchmark cho mỗi bài toán
PLAN = {
    "pipes": ["dfs", "hc"],
    "tents": ["dfs", "astar"],
    "nqueens": ["dfs", "bfs", "astar", "hc"],
}

# So sánh biến thể (bảng PHỤ cho phần giải thích trong báo cáo, không phải bảng chính).
# Chạy: python -m core.benchmark --variants  -> results/benchmark_variants.csv
#   name    : nhãn hiển thị trong CSV và biểu đồ
#   algo    : giải thuật
#   problem : tham số truyền vào load_problem(path, **problem)
#   hc      : ghi đè tham số Hill Climbing (restarts, sideways, seed)
VARIANTS = {
    # Tents (TV3): cùng A*, đổi heuristic -> heuristic có thông tin giúp A* nhanh hơn bao nhiêu
    "tents": [
        {"name": "A* h=tension", "algo": "astar", "problem": {"h_mode": "tension"}},
        {"name": "A* h=naive", "algo": "astar", "problem": {"h_mode": "naive"}},
    ],
    # Pipes (TV2): cùng Hill Climbing h1, có / không đi ngang -> vượt vùng bằng phẳng
    "pipes": [
        {"name": "HC sideways=50", "algo": "hc", "hc": {"sideways": 50}},
        {"name": "HC sideways=0", "algo": "hc", "hc": {"sideways": 0}},
    ],
    # Bài đồ chơi, chỉ để thử chức năng
    "nqueens": [
        {"name": "HC sideways=10", "algo": "hc", "hc": {"sideways": 10}},
        {"name": "HC sideways=0", "algo": "hc", "hc": {"sideways": 0}},
    ],
}


def load_problem(puzzle: str, path: str, **kw):
    if puzzle not in PUZZLES:
        raise ValueError(f"Không có bài toán '{puzzle}'. Chọn một trong {list(PUZZLES)}")
    if not is_available(puzzle):
        owner = {"pipes": "TV2", "tents": "TV3"}.get(puzzle, "")
        raise SystemExit(f"Chưa có {PUZZLES[puzzle].replace('.', '/')}.py {owner}".rstrip()
                         + " - chép puzzles/_template.py để bắt đầu.")
    module = importlib.import_module(PUZZLES[puzzle])
    if not hasattr(module, "load_problem"):
        raise AttributeError(f"Module {PUZZLES[puzzle]} chưa có hàm load_problem(path)")
    return module.load_problem(path, **kw) if kw else module.load_problem(path)


def is_available(puzzle: str) -> bool:
    """True nếu module của bài toán đã tồn tại và import được."""
    try:
        importlib.import_module(PUZZLES[puzzle])
        return True
    except ModuleNotFoundError:
        return False
