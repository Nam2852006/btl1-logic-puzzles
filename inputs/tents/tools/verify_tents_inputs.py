"""Kiểm tra độc lập input/lời giải Tents (không dùng code của script sinh)."""
import glob
import os
import sys
from itertools import product

ORTHO = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def read_input(path):
    with open(path) as f:
        lines = [l.rstrip('\n') for l in f if l.strip()]
    R, C = map(int, lines[0].split())
    grid = lines[1:1 + R]
    rows = list(map(int, lines[1 + R].split()))
    cols = list(map(int, lines[2 + R].split()))
    assert len(grid) == R and all(len(g) == C for g in grid)
    assert len(rows) == R and len(cols) == C
    return R, C, grid, rows, cols


def check_solution(R, C, grid, rows, cols, sol):
    trees = {(r, c) for r in range(R) for c in range(C) if grid[r][c] == 'T'}
    tents = {(r, c) for r in range(R) for c in range(C) if sol[r][c] == 'A'}
    # lưới lời giải phải giữ nguyên cây
    for r in range(R):
        for c in range(C):
            assert (grid[r][c] == 'T') == (sol[r][c] == 'T'), 'cây bị đổi'
    assert len(tents) == len(trees), 'số lều != số cây'
    for (r, c) in tents:
        assert (r, c) not in trees
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr, dc) != (0, 0):
                    assert (r + dr, c + dc) not in tents, 'hai lều chạm nhau'
    for i in range(R):
        assert sum(1 for (r, _) in tents if r == i) == rows[i], f'hàng {i}'
    for j in range(C):
        assert sum(1 for (_, c) in tents if c == j) == cols[j], f'cột {j}'
    # ghép cặp cây-lều 1-1 (Kuhn)
    adj = {t: [(t[0] + dr, t[1] + dc) for dr, dc in ORTHO
               if (t[0] + dr, t[1] + dc) in tents] for t in trees}
    match = {}

    def aug(t, seen):
        for u in adj[t]:
            if u in seen:
                continue
            seen.add(u)
            if u not in match or aug(match[u], seen):
                match[u] = t
                return True
        return False

    for t in trees:
        assert aug(t, set()), 'không ghép cặp 1-1 được'
    return trees, tents


def count_solutions(R, C, trees, rows, cols):
    """Solver độc lập: duyệt theo hàng, mỗi hàng chọn tập cột đặt lều."""
    tree_set = set(trees)
    sols = []

    def row_options(r, prev):
        # chọn rows[r] cột, không kề nhau, không là cây, không chạm hàng trước
        res = []

        def rec(c, chosen):
            if len(chosen) == rows[r]:
                res.append(tuple(chosen))
                return
            for cc in range(c, C):
                if (r, cc) in tree_set:
                    continue
                if chosen and cc - chosen[-1] <= 1:
                    continue
                if any(abs(cc - pc) <= 1 for pc in prev):
                    continue
                rec(cc + 1, chosen + [cc])
        rec(0, [])
        return res

    colc = [0] * C

    def go(r, prev, placed):
        if r == R:
            if colc == cols:
                # mỗi lều phải kề ít nhất 1 cây, và ghép 1-1 được
                sols.append(frozenset(placed))
            return
        for opt in row_options(r, prev):
            ok = True
            for c in opt:
                colc[c] += 1
                if colc[c] > cols[c]:
                    ok = False
            if ok:
                # cắt tỉa: cột không còn khả năng đủ lều
                go(r + 1, opt, placed + [(r, c) for c in opt])
            for c in opt:
                colc[c] -= 1
            if len(sols) > 50000:
                return

    go(0, (), [])
    return sols


def has_matching(trees, tents):
    adj = {t: [(t[0] + dr, t[1] + dc) for dr, dc in ORTHO
               if (t[0] + dr, t[1] + dc) in tents] for t in trees}
    match = {}

    def aug(t, seen):
        for u in adj[t]:
            if u in seen:
                continue
            seen.add(u)
            if u not in match or aug(match[u], seen):
                match[u] = t
                return True
        return False
    return all(aug(t, set()) for t in trees)


def main(d):
    for path in sorted(glob.glob(os.path.join(d, '[0-9][0-9].txt'))):
        if path.endswith('.sol.txt'):
            continue
        R, C, grid, rows, cols = read_input(path)
        with open(path.replace('.txt', '.sol.txt')) as f:
            sl = [l.rstrip('\n') for l in f if l.strip()]
        sol = sl[1:1 + R]
        trees, tents = check_solution(R, C, grid, rows, cols, sol)
        if R <= 12:
            cands = count_solutions(R, C, trees, rows, cols)
            valid = [s for s in cands if len(s) == len(trees) and has_matching(trees, s)]
            status = f'số nghiệm (solver độc lập) = {len(set(valid))}'
        else:
            status = 'bỏ qua solver độc lập (lưới lớn)'
        print(os.path.basename(path), f'{R}x{C}', 'luật OK;', status)


if __name__ == '__main__':
    main(sys.argv[1])
