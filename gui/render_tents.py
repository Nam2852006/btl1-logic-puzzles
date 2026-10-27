"""gui/render_tents.py - Vẽ lưới Tents. Người sở hữu: TV4.

QUY ƯỚC encode() của Tents (theo puzzles/tents.py của TV3):
  Lưới (R+1) x (C+1):
    R hàng đầu, C cột đầu = bàn chơi.   Cột cuối = số lều mỗi hàng (int).
    Hàng cuối = số lều mỗi cột (int).   Ô góc dưới phải = "".
  Ký hiệu ô bàn chơi:
    "T" cây    "A" (hoặc "^") lều    "." ô trống/chưa quyết định    "x" ô cỏ (đã loại)
Nếu lưới không có hàng/cột gợi ý thì GUI vẫn vẽ bàn chơi, chỉ không hiện số.

Cảnh báo trực quan: hai lều chạm nhau (kể cả chéo) viền đỏ; số lều hàng/cột đúng thì
số hiện màu xanh, vượt quá thì màu đỏ.
"""
from __future__ import annotations

import pygame

from gui import theme
from gui.render_grid import fit_cells, mark_changed

SYMBOLS = {"tree": {"T"}, "tent": {"^", "A"}, "grass": {"x", "X"}}
GRASS_A = (132, 214, 100)
GRASS_B = (116, 200, 88)
LEAF = (46, 168, 70)
TRUNK = (150, 92, 52)
TENT_COL = (255, 122, 52)
TENT_STRIPE = (255, 236, 200)


def _is_clue(v):
    return isinstance(v, int) or (isinstance(v, str) and v.strip().isdigit())


def split_grid(grid):
    """Tách (bàn chơi, gợi ý hàng, gợi ý cột). Gợi ý là None nếu không nhận ra."""
    if (len(grid) >= 2 and len(grid[0]) >= 2
            and all(_is_clue(v) for v in grid[-1][:-1])
            and all(_is_clue(row[-1]) for row in grid[:-1])):
        board = [row[:-1] for row in grid[:-1]]
        col_clues = [int(v) for v in grid[-1][:-1]]
        row_clues = [int(row[-1]) for row in grid[:-1]]
        return board, row_clues, col_clues
    return grid, None, None


def _conflicts(board):
    """Tập ô lều chạm nhau (8 hướng)."""
    rows, cols = len(board), len(board[0])
    tents = [(r, c) for r in range(rows) for c in range(cols)
             if str(board[r][c]) in SYMBOLS["tent"]]
    bad = set()
    for i, (r1, c1) in enumerate(tents):
        for r2, c2 in tents[i + 1:]:
            if abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1:
                bad.update({(r1, c1), (r2, c2)})
    return bad


def _ow(cell):
    return max(2, cell // 22)


def _draw_tree(surf, x, y, cell):
    cx, ow = x + cell // 2, _ow(cell)
    trunk = pygame.Rect(cx - cell // 10, y + int(cell * 0.58), max(5, cell // 5), int(cell * 0.30))
    pygame.draw.rect(surf, theme.OUTLINE, trunk.inflate(2 * ow, 2 * ow), border_radius=3)
    pygame.draw.rect(surf, TRUNK, trunk, border_radius=2)
    for dx, dy, rad in [(-0.17, 0.46, 0.22), (0.17, 0.46, 0.22), (0.0, 0.30, 0.26)]:
        pygame.draw.circle(surf, theme.OUTLINE, (cx + int(cell * dx), y + int(cell * dy)), int(cell * rad) + ow)
    for dx, dy, rad in [(-0.17, 0.46, 0.22), (0.17, 0.46, 0.22), (0.0, 0.30, 0.26)]:
        pygame.draw.circle(surf, LEAF, (cx + int(cell * dx), y + int(cell * dy)), int(cell * rad))
    pygame.draw.circle(surf, theme.lighter(LEAF, 0.5), (cx - int(cell * 0.08), y + int(cell * 0.24)),
                       max(2, int(cell * 0.07)))


def _draw_tent(surf, x, y, cell):
    ow = _ow(cell)
    apex = (x + cell // 2, y + int(cell * 0.14))
    left = (x + int(cell * 0.10), y + int(cell * 0.84))
    right = (x + int(cell * 0.90), y + int(cell * 0.84))
    pygame.draw.polygon(surf, TENT_COL, [apex, right, left])
    stripe = [apex, (x + int(cell * 0.62), y + int(cell * 0.84)), (x + int(cell * 0.38), y + int(cell * 0.84))]
    pygame.draw.polygon(surf, TENT_STRIPE, stripe)
    door = [(x + cell // 2, y + int(cell * 0.50)), (x + int(cell * 0.60), y + int(cell * 0.84)),
            (x + int(cell * 0.40), y + int(cell * 0.84))]
    pygame.draw.polygon(surf, (130, 56, 24), door)
    pygame.draw.polygon(surf, theme.OUTLINE, [apex, right, left], ow + 1)
    pygame.draw.circle(surf, theme.YELLOW, apex, max(3, cell // 11))          # cờ nhỏ ở đỉnh lều
    pygame.draw.circle(surf, theme.OUTLINE, apex, max(3, cell // 11), ow)


def _draw_grass(surf, x, y, cell):
    col = theme.darker(GRASS_A, 0.72)
    for dx in (0.30, 0.50, 0.70):
        base = (x + int(cell * dx), y + int(cell * 0.66))
        pygame.draw.line(surf, col, base, (base[0] - 3, base[1] - max(5, cell // 6)), 3)
        pygame.draw.line(surf, col, base, (base[0] + 3, base[1] - max(5, cell // 6)), 3)


def _clue(surf, font, value, have, pos):
    if have == value:
        color = theme.GREEN_LIGHT
    elif have > value:
        color = (255, 120, 108)
    else:
        color = theme.WHITE
    theme.text(surf, font, value, color, pos, "center", outline=theme.OUTLINE, ow=3)


def draw(surf, rect, grid, changed, fonts):
    board, row_clues, col_clues = split_grid(grid)
    rows, cols = len(board), len(board[0]) if board else 0
    if not rows or not cols:
        return
    has_clues = row_clues is not None
    tot_r, tot_c = rows + (1 if has_clues else 0), cols + (1 if has_clues else 0)
    x0, y0, cell = fit_cells(rect, tot_r, tot_c)
    bad = _conflicts(board)

    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * cell, y0 + r * cell
            v = str(board[r][c])
            pygame.draw.rect(surf, GRASS_A if (r + c) % 2 == 0 else GRASS_B, (x, y, cell, cell))
            if v in SYMBOLS["grass"]:
                _draw_grass(surf, x, y, cell)
            elif v in SYMBOLS["tree"]:
                _draw_tree(surf, x, y, cell)
            elif v in SYMBOLS["tent"]:
                _draw_tent(surf, x, y, cell)
    pygame.draw.rect(surf, theme.OUTLINE, (x0, y0, cols * cell, rows * cell), 4)

    for (r, c) in bad:
        x, y = x0 + c * cell, y0 + r * cell
        pygame.draw.rect(surf, theme.OUTLINE, (x - 1, y - 1, cell + 2, cell + 2), 6, border_radius=6)
        pygame.draw.rect(surf, theme.RED, (x + 1, y + 1, cell - 2, cell - 2), 3, border_radius=5)
    for (r, c) in changed:
        if (r, c) not in bad and r < rows and c < cols:
            mark_changed(surf, x0 + c * cell, y0 + r * cell, cell)

    if has_clues:
        font = fonts.sized(max(14, int(cell * 0.5)), bold=True)
        for r in range(rows):
            have = sum(1 for c in range(cols) if str(board[r][c]) in SYMBOLS["tent"])
            _clue(surf, font, row_clues[r], have, (x0 + cols * cell + cell // 2, y0 + r * cell + cell // 2))
        for c in range(cols):
            have = sum(1 for r in range(rows) if str(board[r][c]) in SYMBOLS["tent"])
            _clue(surf, font, col_clues[c], have, (x0 + c * cell + cell // 2, y0 + rows * cell + cell // 2))
