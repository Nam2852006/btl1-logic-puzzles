"""
puzzles/pipes.py — Mô hình hóa bài toán Pipes (puzzle-pipes.com) thành không gian trạng thái.
Người sở hữu: TV2.

LUẬT CHƠI
    Lưới rows x cols, mỗi ô có một đoạn ống (đầu cụt / thẳng / góc / chữ T).
    Chỉ được XOAY từng ô. Lời giải: mọi đầu ống khớp với ô bên cạnh, không đầu nào
    chĩa ra biên, toàn bộ các ô nối thành MỘT mạng duy nhất và KHÔNG có vòng kín
    (tức đồ thị các ô là một cây).

MÃ HÓA MỘT Ô (bitmask các hướng có lỗ)
    Trên = 1, Phải = 2, Dưới = 4, Trái = 8.
    Ví dụ: 4 = đầu cụt quay xuống, A (=2+8) = ống thẳng ngang, C (=8+4) = góc trái-dưới,
    D (=1+8+4) = chữ T mở trên-trái-dưới. Xoay 90° theo chiều kim đồng hồ = xoay vòng 4 bit.

HAI CÁCH BIỂU DIỄN TRẠNG THÁI
    1) Cho DFS (trạng thái "dở dang", gán dần từng ô):
         state = tuple các mask đã chọn cho k ô đầu tiên theo thứ tự hàng -> cột.
         Trạng thái đầu = ()  (chưa gán ô nào); trạng thái đích có đủ rows*cols phần tử.
         Hành động = chọn một góc xoay (một mask) cho ô thứ k.
    2) Cho Hill Climbing (trạng thái "đầy đủ"):
         state = tuple đủ rows*cols mask (mọi ô đều đã có góc xoay, có thể sai).
         Láng giềng = xoay 1 ô, hoặc xoay 2 ô kề nhau quanh một đầu ống đang hở.
    Cả hai đều là tuple (hashable, bất biến) đúng quy ước của core/problem.py, và dùng
    chung goal_test, h, encode (goal_test chỉ đúng khi đủ số ô).

FILE INPUT (inputs/pipes/01.txt ... 05.txt; lời giải đúng ở inputs/pipes/solutions/)
    # dòng chú thích (dòng "# source: i j" = vị trí chấm đỏ trên web, chỉ để vẽ)
    rows cols
    <rows dòng, mỗi dòng cols mã hex cách nhau bởi dấu cách>

Chạy thử:  python main.py --puzzle pipes --algo dfs --input inputs/pipes/03.txt
           python main.py --puzzle pipes --algo hc  --input inputs/pipes/03.txt --restarts 500 --sideways 50
"""
from __future__ import annotations

import random

try:
    from core.problem import Problem          # interface chung của TV1 (trong repo)
except ModuleNotFoundError:                   # chỉ xảy ra khi chạy riêng file này ngoài repo
    class Problem:                            # bản thay thế tối thiểu, không dùng khi nộp
        name = "problem"

        def step_cost(self, state, action):
            return 1

UP, RIGHT, DOWN, LEFT = 1, 2, 4, 8
# hướng -> (dịch dòng, dịch cột, hướng đối diện)
DIRS = {UP: (-1, 0, DOWN), RIGHT: (0, 1, LEFT), DOWN: (1, 0, UP), LEFT: (0, -1, RIGHT)}


# ----------------------------------------------------------------------------
# Tiện ích về ô ống
# ----------------------------------------------------------------------------
def rotate(mask):
    """Xoay một ô 90° theo chiều kim đồng hồ: Trên->Phải->Dưới->Trái->Trên."""
    return ((mask << 1) | (mask >> 3)) & 15


def orientations(mask):
    """Các góc xoay KHÁC NHAU của một ô (ống thẳng có 2, các loại khác có 4)."""
    out = []
    for _ in range(4):
        if mask not in out:
            out.append(mask)
        mask = rotate(mask)
    return out


def load_grid(path):
    """Đọc file input/solution: bỏ dòng '#', dòng đầu là 'rows cols', sau đó là lưới hex.
    Trả về (rows, cols, grid, source) với grid là list các list int."""
    rows = cols = None
    grid, source = [], None
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                if "source" in s:
                    nums = [int(t) for t in s.split(":")[-1].split()]
                    if len(nums) == 2:
                        source = tuple(nums)
                continue
            if rows is None:
                rows, cols = map(int, s.split())
                continue
            row = [int(t, 16) for t in s.split()]
            if len(row) != cols:
                raise ValueError(f"{path}: dòng '{s}' có {len(row)} ô, cần {cols}")
            grid.append(row)
    if rows is None or len(grid) != rows:
        raise ValueError(f"{path}: cần {rows} dòng lưới, đọc được {len(grid)}")
    return rows, cols, grid, source


# ----------------------------------------------------------------------------
# Bài toán
# ----------------------------------------------------------------------------
class PipesProblem(Problem):
    name = "pipes"

    def __init__(self, grid, source=None, heuristic="h1", seed=0, init="greedy"):
        self.rows = len(grid)
        self.cols = len(grid[0])
        self.size = self.rows * self.cols
        self.start_grid = tuple(v for row in grid for v in row)  # góc xoay ban đầu như trên web
        self.source = source
        # các góc xoay hợp lệ của từng ô (loại ống không đổi khi xoay)
        self.options = [orientations(m) for m in self.start_grid]
        if heuristic not in ("h1", "h2"):
            raise ValueError("heuristic phải là 'h1' hoặc 'h2'")
        self.heuristic = heuristic
        if init not in ("uniform", "greedy"):
            raise ValueError("init phải là 'uniform' hoặc 'greedy'")
        self.init = init
        self.rng = random.Random(seed)
        # bảng tra láng giềng: nb[c] = list (hướng, ô kề, hướng đối diện); ô ở biên thì ô kề = -1
        self.nb = []
        for c in range(self.size):
            i, j = divmod(c, self.cols)
            lst = []
            for d, (di, dj, opp) in DIRS.items():
                ii, jj = i + di, j + dj
                inside = 0 <= ii < self.rows and 0 <= jj < self.cols
                lst.append((d, ii * self.cols + jj if inside else -1, opp))
            self.nb.append(lst)
        # Miền giá trị cho Hill Climbing: bỏ sẵn các góc xoay chĩa ra biên (ràng buộc cố định,
        # không phụ thuộc ô khác). DFS vẫn dùng đủ `options`, để is_valid tự loại như slide.
        self.domains = []
        for c in range(self.size):
            out_mask = sum(d for d, nc, _ in self.nb[c] if nc == -1)
            self.domains.append([m for m in self.options[c] if not m & out_mask])

    @classmethod
    def from_file(cls, path, **kw):
        rows, cols, grid, source = load_grid(path)
        return cls(grid, source=source, **kw)

    # ------------------------------------------------------------------ DFS
    def initial_state(self):
        """Chưa gán góc xoay cho ô nào."""
        return ()

    def actions(self, state):
        """Các góc xoay có thể chọn cho ô kế tiếp (ô thứ len(state))."""
        k = len(state)
        if k >= self.size:
            return []
        return list(self.options[k])

    def result(self, state, action):
        """Chốt góc xoay `action` cho ô kế tiếp."""
        return state + (action,)

    def is_valid(self, state):
        """Kiểm tra ô VỪA GÁN (ô cuối của state); các ô trước đã được kiểm tra khi gán.
        Loại nhánh nếu ô vừa gán:
          (a) có lỗ chĩa ra biên;
          (b) không khớp với ô trên hoặc ô trái (đã gán);
          (c) tạo vòng kín;
          (d) làm thành một cụm đã kín hết lỗ trong khi vẫn còn ô chưa gán
              (cụm đó không bao giờ nối được với phần còn lại)."""
        k = len(state) - 1
        if k < 0:
            return True
        m = state[k]
        n_assigned = k + 1
        up_cell = left_cell = -1
        for d, nc, opp in self.nb[k]:
            has = bool(m & d)
            if nc == -1:
                if has:
                    return False                              # (a)
            elif nc < k:                                      # ô trên hoặc ô trái, đã gán
                if has != bool(state[nc] & opp):
                    return False                              # (b)
                if has:
                    if d == UP:
                        up_cell = nc
                    else:
                        left_cell = nc
        # (c) vòng: ô mới nối cả lên trên lẫn sang trái, mà hai ô đó vốn đã cùng một cụm
        if up_cell != -1 and left_cell != -1:
            if self._reachable(state, up_cell, left_cell, n_assigned, banned=k):
                return False
        # (d) cụm chứa ô mới không còn lỗ nào hướng tới ô chưa gán
        if n_assigned < self.size and not self._component_open(state, k, n_assigned):
            return False
        return True

    def _linked(self, state, c, n_assigned):
        """Các ô đã gán nối trực tiếp với ô c (hai bên đều có lỗ quay vào nhau)."""
        m = state[c]
        for d, nc, opp in self.nb[c]:
            if m & d and 0 <= nc < n_assigned:
                yield nc

    def _reachable(self, state, a, b, n_assigned, banned):
        seen, stack = {a, banned}, [a]
        while stack:
            c = stack.pop()
            if c == b:
                return True
            for nc in self._linked(state, c, n_assigned):
                if nc not in seen:
                    seen.add(nc)
                    stack.append(nc)
        return False

    def _component_open(self, state, start, n_assigned):
        """Cụm chứa `start` còn ít nhất một lỗ hướng tới ô chưa gán hay không."""
        seen, stack = {start}, [start]
        while stack:
            c = stack.pop()
            m = state[c]
            for d, nc, opp in self.nb[c]:
                if m & d:
                    if nc >= n_assigned:
                        return True
                    if nc >= 0 and nc not in seen:
                        seen.add(nc)
                        stack.append(nc)
        return False

    def goal_test(self, state):
        """Đích: đủ mọi ô, mọi lỗ khớp, không chĩa ra biên, liên thông, không vòng."""
        if len(state) != self.size:
            return False
        return self.mismatches(state) == 0 and self.components_and_cycles(state) == (1, 0)

    # ---------------------------------------------------- heuristic / đo lỗi
    def mismatches(self, state):
        """Số đầu ống "hở": chĩa ra biên, hoặc chĩa vào ô kề không có lỗ quay lại."""
        bad = 0
        for c in range(self.size):
            m = state[c]
            for d, nc, opp in self.nb[c]:
                if m & d and (nc == -1 or not state[nc] & opp):
                    bad += 1
        return bad

    def components_and_cycles(self, state):
        """(số cụm liên thông, số vòng độc lập) của đồ thị chỉ gồm các cạnh khớp hai đầu.
        Số vòng = số cạnh - số ô + số cụm (công thức chu số của đồ thị)."""
        parent = list(range(self.size))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        edges = 0
        for c in range(self.size):
            m = state[c]
            for d, nc, opp in self.nb[c]:
                if d not in (RIGHT, DOWN):              # mỗi cạnh chỉ xét một lần
                    continue
                if m & d and nc != -1 and state[nc] & opp:
                    edges += 1
                    parent[find(c)] = find(nc)
        comps = sum(1 for c in range(self.size) if find(c) == c)
        return comps, edges - self.size + comps

    def h(self, state):
        """Ước lượng "khoảng cách" tới đích; h = 0 khi và chỉ khi (với h2) là lời giải.
          h1 (local heuristic)  = số đầu ống hở.
          h2 (global heuristic) = h1 + (số cụm - 1) + số vòng.
        Với trạng thái dở dang của DFS, chỉ xét các ô đã gán (ô chưa gán coi như trống)."""
        if len(state) < self.size:
            state = tuple(state) + (0,) * (self.size - len(state))
        h1 = self.mismatches(state)
        if self.heuristic == "h1":
            return h1
        comps, cycles = self.components_and_cycles(state)
        return h1 + (comps - 1) + cycles

    # ------------------------------------------------------- Hill Climbing
    def start_state(self):
        """Trạng thái đầy đủ đúng như màn chơi trên web (góc xoay ban đầu của input)."""
        return self.start_grid

    def random_state(self, rng=None):
        """Điểm xuất phát cho mỗi lần (re)start của Hill Climbing.
        core.search.hill_climbing truyền rng = random.Random(seed) vào, nên cùng seed
        thì cùng kết quả. Không truyền thì dùng self.rng của bài toán."""
        r = rng or self.rng
        if self.init == "uniform":
            return tuple(r.choice(opts) for opts in self.domains)
        # "greedy": đi theo hàng -> cột, mỗi ô chọn ngẫu nhiên trong các góc khớp với ô trên
        # và ô trái đã đặt; nếu không có góc nào khớp thì chọn ngẫu nhiên trong miền.
        st = []
        for c in range(self.size):
            ok = []
            for m in self.domains[c]:
                good = True
                for d, nc, opp in self.nb[c]:
                    if 0 <= nc < c and bool(m & d) != bool(st[nc] & opp):
                        good = False
                        break
                if good:
                    ok.append(m)
            st.append(r.choice(ok or self.domains[c]))
        return tuple(st)

    def neighbors(self, state):
        """Láng giềng gồm 2 loại:
          (1) xoay đúng 1 ô sang góc khác (trong miền không chĩa ra biên);
          (2) xoay ĐỒNG THỜI 2 ô kề nhau, chỉ xét các cặp quanh một đầu ống đang hở.
        Loại (2) là cách thoát "ridge" trong slide chương 3: có những trường hợp phải
        thực hiện hai bước liền nhau thì h mới giảm, còn từng bước riêng lẻ thì không."""
        out = []
        st = list(state)
        for c in range(self.size):
            for m in self.domains[c]:
                if m != state[c]:
                    st[c] = m
                    out.append(tuple(st))
            st[c] = state[c]
        # các ô có đầu ống hở
        bad = set()
        for c in range(self.size):
            m = state[c]
            for d, nc, opp in self.nb[c]:
                if nc != -1 and bool(m & d) != bool(state[nc] & opp):
                    bad.add(c)
        pairs = set()
        for c in bad:
            for d, nc, _ in self.nb[c]:
                if nc != -1:
                    pairs.add((min(c, nc), max(c, nc)))
        for a, b in sorted(pairs):
            for ma in self.domains[a]:
                if ma == state[a]:
                    continue
                st[a] = ma
                for mb in self.domains[b]:
                    if mb != state[b]:
                        st[b] = mb
                        out.append(tuple(st))
                st[b] = state[b]
            st[a] = state[a]
        return out

    # ------------------------------------------------------------------ GUI
    def encode(self, state):
        """Lưới rows x cols các chuỗi 1 ký tự để GUI vẽ và lưu vào file trace, cùng định dạng
        với file input: "0".."F" = mask hex các lỗ của ô (Trên=1, Phải=2, Dưới=4, Trái=8);
        "." = ô chưa gán (trạng thái dở dang của DFS). TV4 đổi lại số bằng int(c, 16)."""
        flat = ["%X" % m for m in state] + ["."] * (self.size - len(state))
        return [flat[i * self.cols:(i + 1) * self.cols] for i in range(self.rows)]

    def size_label(self):
        return f"{self.rows}x{self.cols}"


def load_problem(path: str) -> PipesProblem:
    """Hàm bắt buộc theo core/registry.py: đọc file input, trả về bài toán."""
    return PipesProblem.from_file(path)
