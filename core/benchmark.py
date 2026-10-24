"""
core/benchmark.py — Đo thời gian, bộ nhớ, số nút cho mọi cặp
(bài toán, giải thuật, input), xuất CSV và biểu đồ cho báo cáo.
Người sở hữu: TV1.

Cách chạy (từ thư mục gốc của dự án):
    python -m core.benchmark                         # chạy pipes + tents
    python -m core.benchmark --puzzles nqueens       # chạy bài đồ chơi để thử
    python -m core.benchmark --timeout 60 --repeats 1  # chạy nhanh khi đang thử

Phương pháp đo (ghi vào báo cáo):
  - Thời gian: time.perf_counter(), chạy --repeats lần, lấy TRUNG VỊ.
  - Bộ nhớ: tracemalloc, lấy bộ nhớ ĐỈNH (peak) trong lúc giải thuật chạy,
    đo ở một lần chạy RIÊNG vì tracemalloc làm chương trình chậm đi đáng kể.
  - Chỉ đo phần giải thuật: việc đọc file input nằm ngoài vùng đo.
  - Mỗi lần chạy nằm trong một tiến trình con riêng; quá --timeout giây thì
    bị dừng và ghi status = "timeout".
  - Hill Climbing dùng seed cố định nên các lần chạy cho cùng kết quả.
  - Toàn bộ benchmark phải chạy trên CÙNG MỘT máy để số liệu so sánh được.
"""
from __future__ import annotations

import argparse
import csv
import glob
import multiprocessing as mp
import os
import platform
import queue as queue_mod
import statistics
import sys
import time
import tracemalloc

from core.registry import PLAN, PUZZLES, is_available, load_problem
from core.search import run

FIELDS = ["puzzle", "input", "size", "algorithm", "status", "success",
          "time_s", "peak_kb", "nodes_expanded", "nodes_generated",
          "max_frontier", "restarts", "note"]


# ----------------------------------------------------------------------
# Tiến trình con
# ----------------------------------------------------------------------
def _worker(puzzle, algo, input_path, mode, hc_kwargs, out_q):
    try:
        problem = load_problem(puzzle, input_path)        # ngoài vùng đo
        if mode == "time":
            t0 = time.perf_counter()
            res = run(algo, problem, tracer=None, **hc_kwargs)
            elapsed = time.perf_counter() - t0
            out_q.put({
                "ok": True, "time_s": elapsed, "size": problem.size_label(),
                "success": res.success, "nodes_expanded": res.nodes_expanded,
                "nodes_generated": res.nodes_generated, "max_frontier": res.max_frontier,
                "restarts": res.restarts, "note": res.note,
            })
        else:  # mode == "memory"
            tracemalloc.start()
            run(algo, problem, tracer=None, **hc_kwargs)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            out_q.put({"ok": True, "peak_kb": peak / 1024})
    except Exception as exc:                               # noqa: BLE001
        out_q.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _run_isolated(puzzle, algo, input_path, mode, hc_kwargs, timeout):
    """Chạy _worker trong tiến trình con. Trả về (status, dữ liệu)."""
    ctx = mp.get_context("spawn")      # chạy giống nhau trên Windows/macOS/Linux
    out_q = ctx.Queue()
    proc = ctx.Process(target=_worker,
                       args=(puzzle, algo, input_path, mode, hc_kwargs, out_q))
    proc.start()
    deadline = time.monotonic() + timeout
    data = None
    while time.monotonic() < deadline:
        try:
            data = out_q.get(timeout=0.5)
            break
        except queue_mod.Empty:
            if not proc.is_alive():                # chết mà không trả kết quả
                try:
                    data = out_q.get(timeout=0.5)
                except queue_mod.Empty:
                    data = {"ok": False, "error": f"tiến trình con thoát, mã {proc.exitcode}"}
                break
    if proc.is_alive():
        proc.terminate()
    proc.join()
    if data is None:
        return "timeout", {}
    if not data.get("ok"):
        return "error", data
    return "ok", data


# ----------------------------------------------------------------------
# Một cặp (puzzle, algo, input)
# ----------------------------------------------------------------------
def measure_one(puzzle, algo, input_path, timeout, repeats, hc_kwargs):
    row = {k: "" for k in FIELDS}
    row.update(puzzle=puzzle, algorithm=algo, input=os.path.basename(input_path))

    times = []
    first = None
    for _ in range(repeats):
        status, data = _run_isolated(puzzle, algo, input_path, "time", hc_kwargs, timeout)
        if status != "ok":
            row["status"] = status
            row["note"] = data.get("error", f"vượt {timeout} s") if data else f"vượt {timeout} s"
            row["success"] = False
            row["time_s"] = f">{timeout}" if status == "timeout" else ""
            return row
        times.append(data["time_s"])
        first = first or data

    status, mem = _run_isolated(puzzle, algo, input_path, "memory", hc_kwargs, timeout * 3)
    row.update(
        status="ok",
        size=first["size"],
        success=first["success"],
        time_s=f"{statistics.median(times):.6f}",
        peak_kb=f"{mem['peak_kb']:.1f}" if status == "ok" else "",
        nodes_expanded=first["nodes_expanded"],
        nodes_generated=first["nodes_generated"],
        max_frontier=first["max_frontier"],
        restarts=first["restarts"] if algo == "hc" else "",
        note=first["note"] if status == "ok" else f"đo bộ nhớ: {status}",
    )
    return row


# ----------------------------------------------------------------------
# Biểu đồ
# ----------------------------------------------------------------------
def make_charts(rows, out_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Chưa cài matplotlib, bỏ qua bước vẽ biểu đồ.")
        return []

    os.makedirs(out_dir, exist_ok=True)
    metrics = [("time_s", "Thời gian (giây)"),
               ("peak_kb", "Bộ nhớ đỉnh (KB)"),
               ("nodes_expanded", "Số nút mở rộng")]
    saved = []
    for puzzle in sorted({r["puzzle"] for r in rows}):
        prow = [r for r in rows if r["puzzle"] == puzzle]
        inputs = sorted({r["input"] for r in prow})
        algos = [a for a in PLAN.get(puzzle, []) if any(r["algorithm"] == a for r in prow)] \
            or sorted({r["algorithm"] for r in prow})
        width = 0.8 / max(len(algos), 1)
        for key, label in metrics:
            fig, ax = plt.subplots(figsize=(max(6, 1.4 * len(inputs)), 4))
            for i, algo in enumerate(algos):
                xs, ys, timeouts = [], [], []
                for j, inp in enumerate(inputs):
                    r = next((r for r in prow if r["algorithm"] == algo and r["input"] == inp), None)
                    x = j + (i - (len(algos) - 1) / 2) * width
                    if r is None:
                        continue
                    if r["status"] == "timeout":
                        timeouts.append(x)
                        continue
                    try:
                        y = float(r[key])
                    except (TypeError, ValueError):
                        continue
                    xs.append(x)
                    ys.append(max(y, 1e-6))
                bars = ax.bar(xs, ys, width, label=algo.upper())
                color = bars.patches[0].get_facecolor() if bars.patches else None
                for x in timeouts:
                    # x theo dữ liệu, y theo tỉ lệ trục (0.02 = sát đáy)
                    ax.text(x, 0.02, "timeout", rotation=90, ha="center", va="bottom",
                            fontsize=8, color=color, transform=ax.get_xaxis_transform())
            ax.set_yscale("log")
            ax.set_xticks(range(len(inputs)))
            sizes = []
            for inp in inputs:
                r = next((r for r in prow if r["input"] == inp and r["size"]), None)
                sizes.append(f"{inp}\n{r['size']}" if r else inp)
            ax.set_xticklabels(sizes, fontsize=8)
            ax.set_ylabel(label + " - thang log")
            ax.set_title(f"{puzzle.capitalize()}: {label}")
            ax.legend()
            ax.grid(axis="y", alpha=0.3)
            fig.tight_layout()
            path = os.path.join(out_dir, f"{puzzle}_{key}.png")
            fig.savefig(path, dpi=150)
            plt.close(fig)
            saved.append(path)
    return saved


# ----------------------------------------------------------------------
# Chương trình chính
# ----------------------------------------------------------------------
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Benchmark BTL1")
    p.add_argument("--puzzles", nargs="+", choices=list(PUZZLES), default=None,
                   help="mặc định: pipes và tents (những bài đã có code)")
    p.add_argument("--algos", nargs="+", default=None,
                   help="ghi đè danh sách giải thuật trong core/registry.py (PLAN)")
    p.add_argument("--timeout", type=float, default=300, help="giây cho mỗi lần chạy")
    p.add_argument("--repeats", type=int, default=3, help="số lần đo thời gian, lấy trung vị")
    p.add_argument("--out", default=os.path.join("results", "benchmark.csv"))
    p.add_argument("--charts", default=os.path.join("results", "charts"))
    p.add_argument("--restarts", type=int, default=20)
    p.add_argument("--sideways", type=int, default=0)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    puzzles = args.puzzles or [pz for pz in ("pipes", "tents") if is_available(pz)]
    if not puzzles:
        print("Chưa có puzzles/pipes.py hoặc puzzles/tents.py.\n"
              "Thử benchmark với bài đồ chơi: python -m core.benchmark --puzzles nqueens")
        return 1

    hc_kwargs = {"restarts": args.restarts, "sideways": args.sideways, "seed": args.seed}
    print(f"Máy: {platform.platform()} | Python {platform.python_version()} | "
          f"CPU: {platform.processor() or 'không rõ'}")
    print(f"timeout={args.timeout}s, repeats={args.repeats}, HC={hc_kwargs}\n")

    rows = []
    for puzzle in puzzles:
        if not is_available(puzzle):
            print(f"[bỏ qua] {puzzle}: chưa có module {PUZZLES[puzzle]}")
            continue
        inputs = sorted(glob.glob(os.path.join("inputs", puzzle, "*.txt")))
        if not inputs:
            print(f"[bỏ qua] {puzzle}: không có file nào trong inputs/{puzzle}/")
            continue
        for algo in (args.algos or PLAN.get(puzzle, ["dfs"])):
            for path in inputs:
                print(f"  {puzzle:8} {algo:6} {os.path.basename(path):12} ... ", end="", flush=True)
                row = measure_one(puzzle, algo, path, args.timeout, args.repeats, hc_kwargs)
                rows.append(row)
                if row["status"] == "ok":
                    print(f"{'OK ' if row['success'] else 'FAIL'} {float(row['time_s']):9.4f}s "
                          f"{row['peak_kb']:>10} KB  {row['nodes_expanded']} nút")
                else:
                    print(f"{row['status'].upper()} {row['note']}")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Excel đọc đúng tiếng Việt
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nĐã ghi {len(rows)} dòng vào {args.out}")

    for path in make_charts(rows, args.charts):
        print(f"Đã vẽ {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
