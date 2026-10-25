"""
tests/test_pipes.py — test cho puzzles/pipes.py (TV2).
Chạy từ thư mục gốc của repo:   python -m unittest tests.test_pipes -v
Nhóm TestWithTeamEngine chạy DFS / Hill Climbing THẬT của TV1 (core/search.py);
nếu không có thư mục core/ thì nhóm này tự bỏ qua.
"""
import glob, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from puzzles.pipes import PipesProblem, load_grid, orientations, rotate  # noqa: E402

INPUTS = sorted(glob.glob(os.path.join(ROOT, "inputs", "pipes", "*.txt")))


def solution_of(path):
    return os.path.join(os.path.dirname(path), "solutions", os.path.basename(path))


class TestTiles(unittest.TestCase):
    def test_rotate(self):
        self.assertEqual(rotate(1), 2)      # Trên -> Phải
        self.assertEqual(rotate(8), 1)      # Trái -> Trên
        self.assertEqual(rotate(0b0110), 0b1100)

    def test_orientations(self):
        self.assertEqual(len(orientations(0b0101)), 2)   # ống thẳng
        self.assertEqual(len(orientations(0b0011)), 4)   # góc
        self.assertEqual(len(orientations(0b0001)), 4)   # đầu cụt
        self.assertEqual(len(orientations(0b0111)), 4)   # chữ T


class TestInputFiles(unittest.TestCase):
    def test_have_5_inputs(self):
        self.assertGreaterEqual(len(INPUTS), 5)

    def test_input_and_solution_same_tiles(self):
        for f in INPUTS:
            _, _, gi, _ = load_grid(f)
            _, _, gs, _ = load_grid(solution_of(f))
            for ri, rs in zip(gi, gs):
                for a, b in zip(ri, rs):
                    self.assertIn(a, orientations(b), f)


class TestGoalAndValid(unittest.TestCase):
    def test_solution_passes_goal_test(self):
        for f in INPUTS:
            p = PipesProblem.from_file(f)
            _, _, gs, _ = load_grid(solution_of(f))
            sol = tuple(v for row in gs for v in row)
            self.assertTrue(p.goal_test(sol), f)
            self.assertEqual(p.h(sol), 0, f)

    def test_every_prefix_of_solution_is_valid(self):
        """Mọi trạng thái dở dang trên đường đi tới lời giải đều phải qua is_valid."""
        for f in INPUTS:
            p = PipesProblem.from_file(f)
            _, _, gs, _ = load_grid(solution_of(f))
            sol = tuple(v for row in gs for v in row)
            for k in range(1, len(sol) + 1):
                self.assertTrue(p.is_valid(sol[:k]), f"{f} k={k}")

    def test_start_grid_is_not_goal(self):
        for f in INPUTS:
            p = PipesProblem.from_file(f)
            self.assertFalse(p.goal_test(p.start_state()))
            self.assertGreater(p.h(p.start_state()), 0)

    # --- các trạng thái sai cố ý phải bị loại ---
    def test_reject_pointing_out_of_border(self):
        p = PipesProblem([[1, 4], [1, 1]])
        self.assertFalse(p.is_valid((1,)))            # ô (0,0) chĩa lên trên, ra biên

    def test_reject_mismatch_with_left(self):
        p = PipesProblem([[2, 4], [1, 1]])
        self.assertFalse(p.is_valid((2, 4)))          # (0,0) chĩa phải, (0,1) không có lỗ trái

    def test_reject_mismatch_with_up(self):
        p = PipesProblem([[6, 8], [1, 1]])
        self.assertFalse(p.is_valid((6, 8, 2)))       # (0,0) chĩa xuống, (1,0) không có lỗ trên

    def test_reject_loop(self):
        # 2x2 toàn ống góc tạo thành vòng kín
        p = PipesProblem([[6, 12], [3, 9]])
        self.assertTrue(p.is_valid((6, 12, 3)))
        self.assertFalse(p.is_valid((6, 12, 3, 9)))
        self.assertFalse(p.goal_test((6, 12, 3, 9)))

    def test_reject_closed_component(self):
        # (0,0) và (0,1) là hai đầu cụt nối nhau -> cụm kín trong khi còn ô chưa gán
        p = PipesProblem([[2, 8, 4], [1, 1, 1], [1, 1, 1]])
        self.assertTrue(p.is_valid((2,)))
        self.assertFalse(p.is_valid((2, 8)))

    def test_disconnected_full_state_not_goal(self):
        # mọi lỗ đều khớp nhưng tách làm 2 cụm -> h1 = 0 nhưng chưa phải đích, h2 > 0
        grid = [[2, 8], [2, 8]]
        p1 = PipesProblem(grid, heuristic="h1")
        p2 = PipesProblem(grid, heuristic="h2")
        s = (2, 8, 2, 8)
        self.assertFalse(p1.goal_test(s))
        self.assertEqual(p1.h(s), 0)
        self.assertEqual(p2.h(s), 1)


class TestHillClimbingParts(unittest.TestCase):
    def test_neighbors(self):
        p = PipesProblem.from_file(INPUTS[0])
        s = p.start_state()
        s = p.random_state()
        nbs = p.neighbors(s)
        self.assertTrue(nbs)
        for nb in nbs:
            diff = [c for c in range(p.size) if s[c] != nb[c]]
            self.assertIn(len(diff), (1, 2))
            if len(diff) == 2:      # xoay 2 ô thì 2 ô đó phải kề nhau
                (i1, j1), (i2, j2) = (divmod(c, p.cols) for c in diff)
                self.assertEqual(abs(i1 - i2) + abs(j1 - j2), 1)
            for c in diff:          # không bao giờ sinh góc chĩa ra biên
                self.assertIn(nb[c], p.domains[c])

    def test_random_state_reproducible(self):
        import random
        p = PipesProblem.from_file(INPUTS[0])
        self.assertEqual(p.random_state(random.Random(1)), p.random_state(random.Random(1)))

    def test_encode(self):
        p = PipesProblem.from_file(INPUTS[0])
        g = p.encode((p.start_grid[0],))
        self.assertEqual(len(g), p.rows)
        self.assertTrue(all(len(r) == p.cols for r in g))
        self.assertEqual(int(g[0][0], 16), p.start_grid[0])
        self.assertEqual(g[-1][-1], ".")


try:
    from core.search import dfs, hill_climbing
    from core.registry import load_problem as registry_load
    HAVE_CORE = True
except ModuleNotFoundError:
    HAVE_CORE = False


@unittest.skipUnless(HAVE_CORE, "không có core/ của TV1")
class TestWithTeamEngine(unittest.TestCase):
    def test_registry_loads_pipes(self):
        p = registry_load("pipes", INPUTS[0])
        self.assertEqual(p.name, "pipes")
        self.assertEqual(p.size_label(), f"{p.rows}x{p.cols}")

    def test_dfs_solves_all_inputs(self):
        for f in INPUTS:
            res = dfs(PipesProblem.from_file(f))
            self.assertTrue(res.success, f)
            self.assertEqual(len(res.path), len(res.solution))   # mỗi hành động chốt 1 ô

    def test_hill_climbing_small_inputs(self):
        for f in INPUTS[:3]:                                      # 4x4, 5x5, 7x7
            res = hill_climbing(PipesProblem.from_file(f), restarts=500, sideways=50, seed=0)
            self.assertTrue(res.success, f)
            self.assertTrue(PipesProblem.from_file(f).goal_test(res.solution))

    def test_tracer_can_log_partial_and_full_states(self):
        import json
        from core.tracer import Tracer
        p = PipesProblem.from_file(INPUTS[0])
        t = Tracer()
        t.log(p, p.initial_state(), 0)
        t.log(p, p.start_state(), 0, "move")
        json.dumps(t.events)                                     # phải ghi được ra JSON


if __name__ == "__main__":
    unittest.main()
