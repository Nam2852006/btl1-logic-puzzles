"""gui/render_tents.py - Vẽ lưới Tents. Người sở hữu: TV4.

QUY ƯỚC encode() của Tents (cần TV3 xác nhận; chỉ sửa SYMBOLS / split_grid nếu TV3 chọn khác):
  Lưới (R+1) x (C+1):
    R hàng đầu, C cột đầu = bàn chơi.   Cột cuối = số lều mỗi hàng (int).
    Hàng cuối = số lều mỗi cột (int).   Ô góc dưới phải = "".
  Ký hiệu ô bàn chơi:
    "T" cây    "^" lều    "." ô trống/chưa quyết định    "x" ô cỏ (đã loại, không có lều)
Nếu lưới không có hàng/cột gợi ý thì GUI vẫn vẽ bàn chơi, chỉ không hiện số.

Cảnh báo trực quan: hai lều chạm nhau (kể cả chéo) viền đỏ; số lều hàng/cột đúng thì
số hiện màu xanh, vượt quá thì màu đỏ.
"""
from __future__ import annotations

import pygame

from gui import theme
from gui.render_grid import fit_cells, mark_changed

SYMBOLS = {"tree": {"T"}, "tent": {"^", "A"}, "grass": {"x", "X"}}
GRASS_BG = (226, 240, 217)
TREE_DARK = (34, 110, 52)
TRUNK = (120, 78, 44)
TENT_COL = (232, 120, 30)


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


def _draw_tree(surf, x, y, cell):
    cx = x + cell // 2
    pygame.draw.rect(surf, TRUNK, (cx - cell // 14, y + int(cell * 0.62), max(3, cell // 7), int(cell * 0.26)))
    pygame.draw.circle(surf, TREE_DARK, (cx, y + int(cell * 0.42)), int(cell * 0.30))


def _draw_tent(surf, x, y, cell):
    pts = [(x + cell // 2, y + int(cell * 0.16)),
           (x + int(cell * 0.86), y + int(cell * 0.82)),
           (x + int(cell * 0.14), y + int(cell * 0.82))]
    pygame.draw.polygon(surf, TENT_COL, pts)
    door = [(x + cell // 2, y + int(cell * 0.46)),
            (x + int(cell * 0.60), y + int(cell * 0.82)),
            (x + int(cell * 0.40), y + int(cell * 0.82))]
    pygame.draw.polygon(surf, (120, 54, 10), door)


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
            pygame.draw.rect(surf, GRASS_BG, (x, y, cell, cell))
            if v in SYMBOLS["tree"]:
                _draw_tree(surf, x, y, cell)
            elif v in SYMBOLS["tent"]:
                _draw_tent(surf, x, y, cell)
            elif v in SYMBOLS["grass"]:
                pygame.draw.circle(surf, (150, 190, 140), (x + cell // 2, y + cell // 2), max(2, cell // 12))
            pygame.draw.rect(surf, (190, 210, 182), (x, y, cell, cell), 1)
            if (r, c) in bad:
                pygame.draw.rect(surf, theme.BAD, (x, y, cell, cell), 3)
            elif (r, c) in changed:
                mark_changed(surf, x, y, cell)

    if has_clues:
        font = fonts.sized(max(12, int(cell * 0.42)), bold=True)
        for r in range(rows):
            have = sum(1 for c in range(cols) if str(board[r][c]) in SYMBOLS["tent"])
            color = theme.GOOD if have == row_clues[r] else (theme.BAD if have > row_clues[r] else theme.MUTED)
            theme.text(surf, font, row_clues[r], color,
                       (x0 + cols * cell + cell // 2, y0 + r * cell + cell // 2), "center")
        for c in range(cols):
            have = sum(1 for r in range(rows) if str(board[r][c]) in SYMBOLS["tent"])
            color = theme.GOOD if have == col_clues[c] else (theme.BAD if have > col_clues[c] else theme.MUTED)
            theme.text(surf, font, col_clues[c], color,
                       (x0 + c * cell + cell // 2, y0 + rows * cell + cell // 2), "center")
