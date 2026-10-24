"""
core/check.py — Kiểm tra tự động code của một bài toán có đúng interface không.
Người sở hữu: TV1. TV2, TV3 nên tự chạy trước khi tạo Pull Request.

Cách chạy (từ thư mục gốc):
    python -m core.check pipes inputs/pipes/01.txt
    python -m core.check tents inputs/tents/01.txt --timeout 30

Những gì được kiểm tra:
    1. Có hàm load_problem(path) và trả về đối tượng Problem
    2. Trạng thái hashable (tuple, không phải list)
    3. result() và neighbors() KHÔNG sửa trạng thái cũ
    4. is_valid(), goal_test() trả về bool; h() trả về số không âm
    5. encode() trả về list các list và chuyển được sang JSON
    6. random_state() cho cùng kết quả với cùng seed (nếu dùng Hill Climbing)
    7. Chạy thử từng giải thuật trong PLAN với giới hạn thời gian
"""
from __future__ import annotations

import argparse
import copy
import json
import numbers
import random
import sys

from core.problem import Problem
from core.registry import PLAN, load_problem

PASS, FAIL, WARN = "[ OK ]", "[LỖI]", "[CHÚ Ý]"


class Checker:
    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def ok(self, msg):
        print(f"  {PASS} {msg}")

    def fail(self, msg, hint=""):
        self.errors += 1
        print(f"  {FAIL} {msg}")
        if hint:
            print(f"         -> {hint}")

    def warn(self, msg, hint=""):
        self.warnings += 1
        print(f"  {WARN} {msg}")
        if hint:
            print(f"         -> {hint}")


def _short(x, n=80):
    s = repr(x)
    return s if len(s) <= n else s[:n] + "..."


def check_hashable(c, state, where):
    try:
        hash(state)
        return True
    except TypeError:
        c.fail(f"{where}: trạng thái không hashable: {_short(state)}",
               "Dùng tuple thay cho list, ví dụ tuple(tuple(row) for row in grid)")
        return False


def check_not_mutated(c, before, state, where):
    if before != state:
        c.fail(f"{where} đã SỬA trạng thái cũ",
               "Tạo bản sao mới rồi sửa trên bản sao, không gán trực tiếp vào state")
        return False
    return True


def check_encode(c, problem, state, where):
    try:
        grid = problem.encode(state)
    except NotImplementedError:
        c.fail(f"{where}: chưa cài encode()")
        return
    if not isinstance(grid, list) or not all(isinstance(r, list) for r in grid):
        c.fail(f"{where}: encode() phải trả về list các list, nhận được {type(grid).__name__}",
               "Ví dụ: [['T', '.', 'C'], ['.', '.', '.']]")
        return
    try:
        json.dumps(grid)
    except TypeError as exc:
        c.fail(f"{where}: encode() không chuyển được sang JSON ({exc})",
               "Chỉ dùng str, int, float, bool hoặc None trong mỗi ô")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kiểm tra code bài toán theo interface")
    ap.add_argument("puzzle")
    ap.add_argument("input")
    ap.add_argument("--timeout", type=float, default=20, help="giây cho mỗi giải thuật")
    ap.add_argument("--walk", type=int, default=200, help="số bước đi ngẫu nhiên để kiểm tra")
    args = ap.parse_args(argv)

    c = Checker()
    algos = PLAN.get(args.puzzle, ["dfs"])
    print(f"Kiểm tra '{args.puzzle}' với {args.input} (giải thuật: {', '.join(algos)})\n")

    # 1. load_problem
    print("1. Đọc input")
    try:
        problem = load_problem(args.puzzle, args.input)
    except SystemExit as exc:
        print(f"  {FAIL} {exc}")
        return 1
    except Exception as exc:                                  # noqa: BLE001
        c.fail(f"load_problem() báo lỗi: {type(exc).__name__}: {exc}")
        return 1
    if not isinstance(problem, Problem):
        c.fail("load_problem() không trả về đối tượng kế thừa Problem")
        return 1
    c.ok(f"load_problem() trả về {type(problem).__name__} {problem.size_label()}")

    # 2-5. Trạng thái đầu và đi ngẫu nhiên trong không gian trạng thái
    print("\n2. Trạng thái đầu và các hàm DFS/A*")
    try:
        s0 = problem.initial_state()
    except Exception as exc:                                  # noqa: BLE001
        c.fail(f"initial_state() báo lỗi: {type(exc).__name__}: {exc}")
        return 1
    if check_hashable(c, s0, "initial_state()"):
        c.ok("initial_state() hashable")
    check_encode(c, problem, s0, "initial_state()")

    for name in ("is_valid", "goal_test"):
        v = getattr(problem, name)(s0)
        if not isinstance(v, bool):
            c.fail(f"{name}() phải trả về True/False, nhận được {_short(v)}")
    hv = problem.h(s0)
    if not isinstance(hv, numbers.Real) or hv < 0:
        c.fail(f"h() phải trả về số không âm, nhận được {_short(hv)}")

    rng = random.Random(0)
    state, steps, seen_actions, err_before = s0, 0, 0, c.errors
    for _ in range(args.walk):
        acts = problem.actions(state)
        if not isinstance(acts, list):
            c.fail(f"actions() phải trả về list, nhận được {type(acts).__name__}")
            break
        if not acts:
            break
        seen_actions += len(acts)
        valid_children = []
        for a in acts[:10]:
            before = copy.deepcopy(state)
            child = problem.result(state, a)
            if not check_not_mutated(c, before, state, f"result(state, {_short(a, 30)})"):
                break
            if not check_hashable(c, child, f"result(state, {_short(a, 30)})"):
                break
            if problem.is_valid(child):
                valid_children.append(child)
        if c.errors > err_before:
            break
        if not valid_children:
            break
        state = rng.choice(valid_children)
        steps += 1
        if steps % 20 == 0:
            check_encode(c, problem, state, f"trạng thái ở bước {steps}")
            hv = problem.h(state)
            if not isinstance(hv, numbers.Real) or hv < 0:
                c.fail(f"h() trả về {_short(hv)} ở bước {steps}")
                break
    if c.errors == err_before:
        c.ok(f"Đi ngẫu nhiên {steps} bước: result() không sửa state cũ, mọi state hashable")
    if seen_actions == 0:
        c.warn("actions(initial_state) rỗng: DFS sẽ không đi được bước nào")

    # 6. Hill Climbing
    if "hc" in algos:
        print("\n3. Các hàm Hill Climbing")
        try:
            a = problem.random_state(random.Random(42))
            b = problem.random_state(random.Random(42))
            if a != b:
                c.fail("random_state() cho kết quả khác nhau với cùng seed",
                       "Chỉ dùng rng được truyền vào, không dùng random.choice(...) toàn cục")
            elif check_hashable(c, a, "random_state()"):
                c.ok("random_state() hashable và lặp lại được với cùng seed")
            before = copy.deepcopy(a)
            nbrs = problem.neighbors(a)
            check_not_mutated(c, before, a, "neighbors()")
            if not isinstance(nbrs, list) or not nbrs:
                c.fail("neighbors() phải trả về list khác rỗng")
            elif all(check_hashable(c, n, "neighbors()") for n in nbrs[:20]):
                c.ok(f"neighbors() trả về {len(nbrs)} láng giềng hashable")
            check_encode(c, problem, a, "random_state()")
        except NotImplementedError as exc:
            c.fail(str(exc))

    # 7. Chạy thử giải thuật
    print(f"\n4. Chạy thử giải thuật (tối đa {args.timeout:g} s mỗi giải thuật)")
    if c.errors:
        print("  Bỏ qua vì còn lỗi ở trên.")
    else:
        from core.benchmark import _run_isolated
        hc_kwargs = {"restarts": 20, "sideways": 0, "seed": 0}
        for algo in algos:
            status, data = _run_isolated(args.puzzle, algo, args.input, "time",
                                         hc_kwargs, args.timeout)
            if status == "ok" and data["success"]:
                c.ok(f"{algo}: tìm thấy lời giải trong {data['time_s']:.3f} s, "
                     f"{data['nodes_expanded']} nút mở rộng")
            elif status == "ok":
                c.warn(f"{algo}: chạy xong nhưng KHÔNG tìm thấy lời giải ({data['note']})",
                       "Kiểm tra goal_test() và is_valid(); với Hill Climbing thử tăng --restarts")
            elif status == "timeout":
                c.warn(f"{algo}: vượt {args.timeout:g} s",
                       "Bình thường với input lớn; với input nhỏ thì is_valid() có thể chưa cắt nhánh đủ")
            else:
                c.fail(f"{algo}: lỗi khi chạy: {data.get('error')}")

    print(f"\nKết quả: {c.errors} lỗi, {c.warnings} chú ý.")
    if c.errors == 0:
        print("Code đúng interface. Có thể tạo Pull Request.")
    return 1 if c.errors else 0


if __name__ == "__main__":
    sys.exit(main())
