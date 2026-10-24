"""
core/registry.py — Danh sách bài toán và cặp giải thuật của nhóm.
Người sở hữu: TV1.

Mỗi module bài toán PHẢI có hàm:
    load_problem(path: str) -> Problem
đọc file input và trả về một đối tượng Problem.
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


def load_problem(puzzle: str, path: str):
    if puzzle not in PUZZLES:
        raise ValueError(f"Không có bài toán '{puzzle}'. Chọn một trong {list(PUZZLES)}")
    if not is_available(puzzle):
        owner = {"pipes": "TV2", "tents": "TV3"}.get(puzzle, "")
        raise SystemExit(f"Chưa có {PUZZLES[puzzle].replace('.', '/')}.py {owner}".rstrip()
                         + " - chép puzzles/_template.py để bắt đầu.")
    module = importlib.import_module(PUZZLES[puzzle])
    if not hasattr(module, "load_problem"):
        raise AttributeError(f"Module {PUZZLES[puzzle]} chưa có hàm load_problem(path)")
    return module.load_problem(path)


def is_available(puzzle: str) -> bool:
    """True nếu module của bài toán đã tồn tại và import được."""
    try:
        importlib.import_module(PUZZLES[puzzle])
        return True
    except ModuleNotFoundError:
        return False
