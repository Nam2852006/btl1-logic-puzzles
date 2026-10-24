"""
main.py — Chạy một cặp (bài toán, giải thuật, input).
Người sở hữu: TV1.

Ví dụ:
    python main.py --puzzle nqueens --algo dfs --input inputs/nqueens/08.txt
    python main.py --puzzle nqueens --algo hc --input inputs/nqueens/08.txt --restarts 50
    python main.py --puzzle tents --algo astar --input inputs/tents/01.txt --trace
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from core.registry import PUZZLES, load_problem
from core.search import ALGORITHMS, run
from core.tracer import Tracer


def print_grid(grid) -> None:
    for row in grid:
        print("  " + " ".join(str(c) for c in row))


def main() -> int:
    p = argparse.ArgumentParser(description="BTL1 - Tìm kiếm trên Logic Puzzles")
    p.add_argument("--puzzle", choices=list(PUZZLES), required=True)
    p.add_argument("--algo", choices=list(ALGORITHMS), required=True)
    p.add_argument("--input", required=True, help="đường dẫn file input")
    p.add_argument("--trace", nargs="?", const="auto", default=None,
                   help="ghi file trace cho GUI; bỏ trống để tự đặt tên trong results/traces/")
    p.add_argument("--max-trace-steps", type=int, default=5000)
    p.add_argument("--restarts", type=int, default=20, help="Hill Climbing: số lần restart")
    p.add_argument("--sideways", type=int, default=0, help="Hill Climbing: số bước đi ngang")
    p.add_argument("--seed", type=int, default=0, help="Hill Climbing: hạt giống ngẫu nhiên")
    args = p.parse_args()

    problem = load_problem(args.puzzle, args.input)
    tracer = Tracer(args.max_trace_steps) if args.trace else None

    print(f"Bài toán : {args.puzzle} {problem.size_label()}  ({args.input})")
    print(f"Giải thuật: {args.algo}")

    t0 = time.perf_counter()
    result = run(args.algo, problem, tracer=tracer,
                 restarts=args.restarts, sideways=args.sideways, seed=args.seed)
    elapsed = time.perf_counter() - t0

    print(result.summary())
    print(f"  Thời gian        : {elapsed:.4f} s"
          + ("  (đã bật trace nên chậm hơn bình thường)" if tracer else ""))

    if result.success:
        print("Lời giải:")
        print_grid(problem.encode(result.solution))

    if tracer is not None:
        if args.trace == "auto":
            base = os.path.splitext(os.path.basename(args.input))[0]
            path = os.path.join("results", "traces", f"{args.puzzle}_{args.algo}_{base}.jsonl")
        else:
            path = args.trace
        meta = {"puzzle": args.puzzle, "algorithm": args.algo, "input": args.input,
                "size": problem.size_label()}
        tracer.save(path, meta, result, problem)
        note = " (đã cắt bớt)" if tracer.truncated else ""
        print(f"Đã ghi trace: {path} - {len(tracer.events)}/{tracer.total_steps} bước{note}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
