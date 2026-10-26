"""Test mô hình Tents. Chạy: python -m unittest tests.test_tents -v (từ thư mục gốc repo)."""
import glob
import math
import os
import unittest

from puzzles.tents import TentsProblem, parse_solution

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUTS = sorted(f for f in glob.glob(os.path.join(ROOT, 'inputs', 'tents', '[0-9][0-9].txt')))


def load(path, **kw):
    p = TentsProblem.from_file(path, **kw)
    sol = p.state_from_tents(parse_solution(path.replace('.txt', '.sol.txt')))
    return p, sol


class TestInputs(unittest.TestCase):
    def test_at_least_5_inputs(self):
        self.assertGreaterEqual(len(INPUTS), 5)

    def test_solution_passes_goal_test(self):
        for path in INPUTS:
            for prune in ('basic', 'full'):
                with self.subTest(file=os.path.basename(path), prune=prune):
                    p, sol = load(path, prune=prune)
                    self.assertIsNotNone(sol, 'không ghép được cây-lều từ lời giải')
                    self.assertTrue(p.goal_test(sol))
                    # mọi tiền tố của lời giải đều hợp lệ (DFS/A* không bao giờ cắt nhầm nhánh đúng)
                    for k in range(len(sol) + 1):
                        self.assertTrue(p.is_valid(sol[:k]), f'cắt nhầm tiền tố độ dài {k}')
                        self.assertNotEqual(p.h(sol[:k]), math.inf, f'h = inf ở tiền tố đúng {k}')


class TestRules(unittest.TestCase):
    def setUp(self):
        self.p, self.sol = load(INPUTS[0])

    def test_initial_state(self):
        s0 = self.p.initial_state()
        self.assertEqual(s0, ())
        self.assertTrue(self.p.is_valid(s0))
        self.assertFalse(self.p.goal_test(s0))

    def test_actions_and_result(self):
        s0 = self.p.initial_state()
        acts = self.p.actions(s0)
        self.assertIn(self.sol[0], acts)
        self.assertEqual(self.p.result(s0, acts[0]), (acts[0],))
        self.assertEqual(self.p.actions(self.sol), [])

    def test_incomplete_is_not_goal(self):
        self.assertFalse(self.p.goal_test(self.sol[:-1]))

    def test_rejects_tent_not_next_to_its_tree(self):
        bad = list(self.sol)
        r, c = self.p.trees[0]
        far = next((x, y) for x in range(self.p.R) for y in range(self.p.C)
                   if abs(x - r) + abs(y - c) > 1 and self.p.grid[x][y] == '.')
        bad[0] = far
        self.assertFalse(self.p.is_valid(tuple(bad)))
        self.assertFalse(self.p.goal_test(tuple(bad)))

    def test_rejects_touching_tents(self):
        # cây (0,0), (2,1). Số hàng/cột cho phép lều (0,1) và (1,1) -> chỉ còn lý do "chạm nhau" để loại
        p = TentsProblem(['T.', '..', '.T'], [1, 1, 0], [0, 2])
        self.assertTrue(p.is_valid(((0, 1),)))
        self.assertFalse(p.is_valid(((0, 1), (1, 1))))          # chạm cạnh
        q = TentsProblem(['T..', '...', '..T'], [1, 1, 0], [0, 1, 1])
        self.assertFalse(q.is_valid(((0, 1), (1, 2))))          # chạm chéo

    def test_rejects_row_col_overflow(self):
        # cây (0,0), (2,2); lời giải: lều (0,1), (2,1)
        p = TentsProblem(['T..', '...', '..T'], [1, 0, 1], [0, 2, 0])
        self.assertTrue(p.is_valid(((0, 1),)))
        self.assertFalse(p.is_valid(((1, 0),)))      # hàng 1 và cột 0 cần 0 lều
        self.assertTrue(p.goal_test(((0, 1), (2, 1))))

    def test_rejects_same_cell_twice(self):
        # cây (0,0), (0,2) cùng kề ô (0,1); lời giải: lều (1,0), (1,2)
        p = TentsProblem(['T.T', '...', '...'], [0, 2, 0], [1, 0, 1])
        self.assertFalse(p.is_valid(((0, 1), (0, 1))))
        self.assertTrue(p.goal_test(((1, 0), (1, 2))))


class TestHeuristic(unittest.TestCase):
    def test_h_zero_at_goal(self):
        for path in INPUTS:
            p, sol = load(path)
            self.assertEqual(p.h(sol), 0)

    def test_naive_is_trees_left(self):
        p, sol = load(INPUTS[-1], h_mode='naive')
        for k in (0, 5, len(sol)):
            self.assertEqual(p.h(sol[:k]), p.T - k)

    def test_tension_not_constant_across_same_depth(self):
        # điểm mấu chốt: ở cùng độ sâu, h phải phân biệt được các nút (tránh f bằng nhau)
        p, sol = load(INPUTS[-1])
        values = set()
        for k in range(1, 30):
            for a in p.actions(sol[:k - 1]):
                child = sol[:k - 1] + (a,)
                if p.is_valid(child) and p.h(child) != math.inf:
                    values.add(round(p.h(child) - (p.T - k), 6))
        self.assertGreater(len(values), 1)

    def test_dead_end_gets_infinite_h(self):
        # trạng thái hợp lệ cục bộ nhưng không thể tới đích -> h = inf (admissible vì h* = inf)
        for path in INPUTS:
            p, sol = load(path)
            for k in range(1, p.T + 1):
                for a in p.actions(sol[:k - 1]):
                    s = sol[:k - 1] + (a,)
                    if a != sol[k - 1] and p.is_valid(s) and p.h(s) == math.inf:
                        return
        self.fail('không tìm thấy ngõ cụt nào được h phát hiện')


class TestEncode(unittest.TestCase):
    def test_encode_matches_solution_file(self):
        for path in INPUTS:
            p, sol = load(path)
            with open(path.replace('.txt', '.sol.txt')) as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            g = p.encode(sol)
            self.assertEqual([row[:-1] for row in g[:-1]], [list(row) for row in lines[1:1 + p.R]])
            self.assertEqual([row[-1] for row in g[:-1]], p.rows)
            self.assertEqual(g[-1], p.cols + [''])
            self.assertEqual([row[:-1] for row in p.encode(())[:-1]], [list(row) for row in p.grid])
            self.assertIsInstance(p.encode(sol)[0], list)

    def test_size_label(self):
        p, _ = load(INPUTS[-1])
        self.assertEqual(p.size_label(), '30x30')

    def test_result_does_not_modify_state(self):
        p, sol = load(INPUTS[0])
        s = sol[:3]
        before = tuple(s)
        child = p.result(s, p.actions(s)[0])
        self.assertEqual(s, before)
        self.assertIsInstance(child, tuple)
        hash(child)


if __name__ == '__main__':
    unittest.main()
