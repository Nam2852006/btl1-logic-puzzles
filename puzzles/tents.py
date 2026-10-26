"""Mô hình hóa Tents (puzzle-tents.com) theo interface Problem của nhóm. TV3 sở hữu.

Luật chơi
    - Mỗi cây có đúng 1 lều ở ô kề cạnh (trên/dưới/trái/phải), mỗi lều thuộc đúng 1 cây.
    - Hai lều không chạm nhau, kể cả chéo.
    - Số lều mỗi hàng/cột bằng số gợi ý.

Định dạng input (inputs/tents/NN.txt)
    dòng 1: R C
    R dòng: lưới, 'T' = cây, '.' = ô trống
    1 dòng: R số = số lều mỗi hàng
    1 dòng: C số = số lều mỗi cột
    Lời giải (NN.sol.txt): dòng 1 'R C', R dòng lưới, 'A' = lều.

Không gian trạng thái
    - Cây đánh số 0..T-1 theo thứ tự hàng rồi cột (row-major).
    - Trạng thái = tuple các ô lều đã đặt, phần tử thứ i là lều của cây i.
      Độ dài tuple = số cây đã xử lý = g(n). Tuple bất biến nên băm được (dùng cho closed set của A*).
    - Trạng thái đầu: tuple rỗng ().
    - Hành động tại trạng thái độ dài k: chọn 1 ô kề cạnh cây k (trong lưới, không phải cây).
    - Hàm chuyển: result(s, a) = s + (a,).
    - Đích: đủ T lều, mọi ràng buộc thỏa và số lều mỗi hàng/cột đúng bằng gợi ý.
    - Mọi lời giải nằm ở cùng độ sâu T, mỗi bước tốn 1.

Dùng (cho TV1 / main.py)
    from puzzles.tents import load_problem
    p = load_problem('inputs/tents/03.txt')                 # mặc định: h_mode='tension', prune='basic'
    p = load_problem(path, h_mode='naive')                  # A* với h = số cây còn lại (để so sánh)
    p = load_problem(path, prune='full')                    # is_valid có thêm forward checking
    p.encode(state)                                         # lưới (R+1)x(C+1) cho GUI, kèm số gợi ý hàng/cột
    p.size_label()                                          # '30x30'
    p.state_from_tents(tents)                               # tập ô lều -> trạng thái (vd. phát lại lời giải)
"""
import math

try:
    from core.problem import Problem          # interface của TV1
except ImportError:                            # chạy độc lập khi chưa có core/
    class Problem:
        def step_cost(self, state, action):
            return 1

ORTHO = ((-1, 0), (1, 0), (0, -1), (0, 1))
AROUND = tuple((dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0))


def parse_input(path):
    """Đọc file input -> (grid: list[str], rows: list[int], cols: list[int])."""
    with open(path, encoding='utf-8') as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    R, C = map(int, lines[0].split())
    grid = lines[1:1 + R]
    rows = [int(x) for x in lines[1 + R].split()]
    cols = [int(x) for x in lines[2 + R].split()]
    if len(grid) != R or any(len(g) != C for g in grid):
        raise ValueError(f'{path}: lưới không đúng kích thước {R}x{C}')
    if any(ch not in 'T.' for g in grid for ch in g):
        raise ValueError(f'{path}: lưới chỉ được chứa "T" và "."')
    if len(rows) != R or len(cols) != C:
        raise ValueError(f'{path}: thiếu/thừa số gợi ý hàng hoặc cột')
    return grid, rows, cols


def parse_solution(path):
    """Đọc file lời giải -> tập ô (r, c) có lều."""
    with open(path, encoding='utf-8') as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    R, _ = map(int, lines[0].split())
    return {(r, c) for r, row in enumerate(lines[1:1 + R]) for c, ch in enumerate(row) if ch == 'A'}


class TentsProblem(Problem):
    """
    h_mode: 'tension' (mặc định, dùng cho A*) hoặc 'naive' (= số cây còn lại, để so sánh).
    prune : 'basic' (mặc định, đúng như kế hoạch nhóm: is_valid chỉ kiểm luật cục bộ - lều chạm
            nhau, vượt số lều hàng/cột) hoặc 'full' (thêm forward checking vào is_valid, DFS mạnh hơn hẳn).
    """

    def __init__(self, grid, rows, cols, h_mode='tension', prune='basic'):
        if h_mode not in ('tension', 'naive') or prune not in ('full', 'basic'):
            raise ValueError('h_mode phải là tension/naive, prune phải là full/basic')
        self.prune = prune
        self.grid = list(grid)
        self.R, self.C = len(grid), len(grid[0])
        self.rows, self.cols = list(rows), list(cols)
        self.trees = [(r, c) for r in range(self.R) for c in range(self.C) if grid[r][c] == 'T']
        self.tree_set = set(self.trees)
        self.T = len(self.trees)
        self.h_mode = h_mode
        # ô ứng viên của từng cây: kề cạnh, trong lưới, không phải cây
        self.cand = [tuple((r + dr, c + dc) for dr, dc in ORTHO
                           if 0 <= r + dr < self.R and 0 <= c + dc < self.C
                           and (r + dr, c + dc) not in self.tree_set)
                     for (r, c) in self.trees]
        if sum(self.rows) != self.T or sum(self.cols) != self.T:
            raise ValueError('tổng gợi ý hàng/cột phải bằng số cây')

    @classmethod
    def from_file(cls, path, **kw):
        return cls(*parse_input(path), **kw)

    # ------------------------------------------------------------------ DFS / A*
    def initial_state(self):
        return ()

    def actions(self, state):
        """Các ô có thể đặt lều cho cây kế tiếp. Chưa lọc ràng buộc: is_valid sẽ loại sau khi sinh nút con."""
        k = len(state)
        return list(self.cand[k]) if k < self.T else []

    def result(self, state, action):
        return state + (action,)

    def step_cost(self, state, action):
        return 1

    def is_valid(self, state):
        """True nếu trạng thái chưa vi phạm luật (và, với prune='full', vẫn còn khả năng tới đích)."""
        if self.prune == 'basic':
            return self._local(state) is not None
        return self._analyse(state) is not None

    def goal_test(self, state):
        if len(state) != self.T or self._local(state) is None:
            return False
        rc, cc = self._counts(state)
        return rc == self.rows and cc == self.cols

    # ------------------------------------------------------------------ heuristic
    def h(self, state):
        """Ước lượng số bước còn lại tới đích (giải thích chi tiết: HEURISTIC_NOTES cuối file)."""
        rest = self.T - len(state)
        if self.h_mode == 'naive':
            return rest
        info = self._analyse(state)
        if info is None:                      # ngõ cụt: h*(n) = vô cùng
            return math.inf
        need_r, cap_r, need_c, cap_c = info
        tension = 0.0
        for need, cap in zip(need_r + need_c, cap_r + cap_c):
            if need > 0:
                tension += need / cap        # cap >= need > 0 vì _analyse đã kiểm tra
        return rest + tension

    # ------------------------------------------------------------------ GUI
    def encode(self, state):
        """Lưới (R+1)x(C+1) cho GUI, theo quy ước của gui/render_tents.py:
        R hàng đầu, C cột đầu là bàn chơi ('T' cây, 'A' lều, '.' trống);
        cột cuối = số lều mỗi hàng, hàng cuối = số lều mỗi cột (int), ô góc dưới phải = ''."""
        g = [list(row) for row in self.grid]
        for (r, c) in state:
            g[r][c] = 'A'
        return [row + [self.rows[r]] for r, row in enumerate(g)] + [list(self.cols) + ['']]

    def size_label(self):
        """Nhãn kích thước cho benchmark/GUI, vd. '30x30'."""
        return f'{self.R}x{self.C}'

    def state_from_tents(self, tents):
        """Chuyển tập ô lều (vd. đọc từ .sol.txt) thành trạng thái đầy đủ (ghép cây-lều). None nếu không ghép được."""
        tents = set(tents)
        match = {}

        def aug(i, seen):
            for cell in self.cand[i]:
                if cell in tents and cell not in seen:
                    seen.add(cell)
                    if cell not in match or aug(match[cell], seen):
                        match[cell] = i
                        return True
            return False

        if len(tents) != self.T or not all(aug(i, set()) for i in range(self.T)):
            return None
        own = {i: cell for cell, i in match.items()}
        return tuple(own[i] for i in range(self.T))

    # ------------------------------------------------------------------ nội bộ
    def _counts(self, state):
        rc, cc = [0] * self.R, [0] * self.C
        for (r, c) in state:
            rc[r] += 1
            cc[c] += 1
        return rc, cc

    def _local(self, state):
        """Bước 1 - luật cục bộ: lều là ô kề của đúng cây đó, không trùng, không chạm lều khác
        (8 hướng), không vượt số lều hàng/cột. Trả về (placed, rc, cc) hoặc None nếu vi phạm."""
        if len(state) > self.T:
            return None
        placed = set()
        rc, cc = [0] * self.R, [0] * self.C
        for i, (r, c) in enumerate(state):
            if (r, c) not in self.cand[i] or (r, c) in placed:
                return None
            for dr, dc in AROUND:
                if (r + dr, c + dc) in placed:
                    return None
            placed.add((r, c))
            rc[r] += 1
            cc[c] += 1
            if rc[r] > self.rows[r] or cc[c] > self.cols[c]:
                return None
        return placed, rc, cc

    def _analyse(self, state):
        """Kiểm tra đầy đủ. Trả về None nếu sai/ngõ cụt, ngược lại (need_r, cap_r, need_c, cap_c).

        need = số lều hàng/cột còn thiếu; cap = số lều tối đa còn đặt thêm được vào hàng/cột đó.
          1. Luật cục bộ (_local).
          2. Forward checking: mỗi cây chưa xử lý phải còn ít nhất 1 ô đặt được; các cây chỉ còn
             đúng 1 lựa chọn không được tranh cùng ô hay chạm nhau.
          3. Mỗi hàng/cột phải còn đủ chỗ: cap >= need.
        """
        loc = self._local(state)
        if loc is None:
            return None
        placed, rc, cc = loc
        k = len(state)

        def free(cell):
            r, c = cell
            if cell in placed or rc[r] >= self.rows[r] or cc[c] >= self.cols[c]:
                return False
            return all((r + dr, c + dc) not in placed for dr, dc in AROUND)

        avail = set()
        reach_r, reach_c = [0] * self.R, [0] * self.C
        forced = []
        for i in range(k, self.T):
            opts = [cell for cell in self.cand[i] if free(cell)]
            if not opts:
                return None
            if len(opts) == 1:
                forced.append(opts[0])
            avail.update(opts)
            for r in {cell[0] for cell in opts}:
                reach_r[r] += 1
            for c in {cell[1] for cell in opts}:
                reach_c[c] += 1
        fset = set()
        for (r, c) in forced:
            if (r, c) in fset or any((r + dr, c + dc) in fset for dr, dc in AROUND):
                return None
            fset.add((r, c))

        # số lều tối đa đặt thêm được trên một hàng = tập ô không kề nhau lớn nhất (tham lam theo cột)
        by_r = [[] for _ in range(self.R)]
        by_c = [[] for _ in range(self.C)]
        for (r, c) in avail:
            by_r[r].append(c)
            by_c[c].append(r)

        def indep(xs):
            n, last = 0, -2
            for x in sorted(xs):
                if x - last > 1:
                    n, last = n + 1, x
            return n

        need_r = [self.rows[r] - rc[r] for r in range(self.R)]
        need_c = [self.cols[c] - cc[c] for c in range(self.C)]
        cap_r = [min(indep(by_r[r]), reach_r[r]) for r in range(self.R)]
        cap_c = [min(indep(by_c[c]), reach_c[c]) for c in range(self.C)]
        if any(n > m for n, m in zip(need_r, cap_r)) or any(n > m for n, m in zip(need_c, cap_c)):
            return None
        return need_r, cap_r, need_c, cap_c


def load_problem(path, **kw):
    return TentsProblem.from_file(path, **kw)


HEURISTIC_NOTES = """
Heuristic cho A* (h_mode='tension')

    h(n) = (T - g(n)) + sum over hàng/cột L có need_L > 0 của need_L / cap_L
    h(n) = vô cùng nếu n là ngõ cụt phát hiện được (một cây hết chỗ, hai cây bị ép vào cùng ô
           hoặc ô chạm nhau, hay một hàng/cột có cap_L < need_L)

    T - g(n)  : số cây chưa có lều = số bước còn lại nếu n còn tới được đích.
    need_L    : số lều hàng/cột L còn thiếu.
    cap_L     : số lều tối đa còn đặt thêm được vào L = min(số cây chưa xử lý còn với tới L,
                số ô trống còn đặt được trên L không kề nhau).
    need/cap  : độ "căng" của L, thuộc (0, 1]; bằng 1 nghĩa là L bị ép, mọi chỗ còn lại phải dùng hết.

Vì sao không dùng h = số cây còn lại (h_mode='naive')
    Mọi lời giải ở cùng độ sâu T, bước tốn 1, nên g + (T - g) = T ở mọi nút: f bằng nhau, A* thoái hóa
    thành tìm kiếm mù (thứ tự mở rộng chỉ còn do cách phá hòa). Cũng vì vậy, với h tension:
    f(n) = T + tension(n), tức A* thực chất là Best-First Search theo tension; nhân tension với
    hệ số bất kỳ không làm đổi thứ tự mở rộng.

Admissible (ký hiệu theo slide chương 3: h(n) = chi phí THẬT tới đích, h*(n) = giá trị ƯỚC LƯỢNG;
hàm h() trong code chính là h*(n); admissible <=> h*(n) <= h(n) với mọi n)
    - Nút còn tới được đích: h(n) = T - g(n) đúng bằng số cây còn lại.
    - Nút ngõ cụt: h(n) = vô cùng.
    - h* = vô cùng ở ngõ cụt: luôn <= h(n), nên phần này admissible (và cắt tỉa được nhánh sai).
    - Phần tension > 0 ở nút còn tới được đích làm h*(n) > h(n): h* KHÔNG admissible.
    - Không ảnh hưởng tính tối ưu: mọi lời giải có cùng chi phí T, nên lời giải nào tìm được
      cũng tối ưu. h* chỉ ảnh hưởng số nút mở rộng.
    - h_mode='naive' (h* = T - g) admissible, thậm chí bằng h(n) ở mọi nút còn tới được đích, nhưng không
      phân biệt được nút tốt/xấu cùng độ sâu nên vô dụng cho A*.

Local hay global heuristic (theo slide chương 3)
    - T - g và need_L là thông tin cục bộ đếm trực tiếp từ trạng thái.
    - cap_L và phát hiện ngõ cụt xét toàn bộ cây chưa xử lý và toàn bộ hàng/cột -> mang tính
      global heuristic: đánh giá cả bàn cờ, không chỉ nước vừa đi.
"""
