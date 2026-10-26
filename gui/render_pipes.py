"""gui/render_pipes.py - Vẽ lưới Pipes. Người sở hữu: TV4.

QUY ƯỚC encode() của Pipes (theo puzzles/pipes.py của TV2, đã thống nhất):
  Mỗi ô là MỘT ký tự hex "0".."F" = bitmask các phía đang HỞ của ô ống sau khi xoay:
    Trên = 1, Phải = 2, Dưới = 4, Trái = 8.
    Ví dụ: "5" = 1+4 = ống thẳng đứng, "A" = 2+8 = ống thẳng ngang,
           "C" = 4+8 = ống cong dưới-trái, "D" = 1+4+8 = chữ T, "4" = đầu cụt quay xuống.
  "." = ô chưa gán (DFS gán dần từng ô). "?" cũng được hiểu là chưa gán.
Vì ô chứa sẵn các phía hở nên GUI không cần biết hình dạng gốc hay góc xoay.

Màu: xanh = phía hở khớp với láng giềng; đỏ = đầu hở không khớp (lỗi, h tăng);
cam = láng giềng chưa gán nên chưa biết.
"""
from __future__ import annotations

import pygame

from gui import theme
from gui.render_grid import fit_cells, mark_changed

DIRS = {"N": (-1, 0, "S"), "E": (0, 1, "W"), "S": (1, 0, "N"), "W": (0, -1, "E")}
PIPE_OK = (37, 99, 235)
PIPE_BAD = (220, 38, 38)
PIPE_PENDING = (234, 138, 0)


# Bit trong mã hex của TV2 -> tên phía dùng trong DIRS
HEX_BITS = {1: "N", 2: "E", 4: "S", 8: "W"}


def parse_cell(v):
    """Trả về (tập phía hở, chưa_gán) từ một ô do encode() của TV2 xuất ra."""
    if v is None or v in (".", "?"):
        return set(), True
    try:
        mask = int(str(v), 16)
    except ValueError:            # ký hiệu lạ: coi như chưa gán thay vì làm hỏng GUI
        return set(), True
    return {name for bit, name in HEX_BITS.items() if mask & bit}, False


def draw(surf, rect, grid, changed, fonts):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if not rows or not cols:
        return
    parsed = [[parse_cell(v) for v in row] for row in grid]
    x0, y0, cell = fit_cells(rect, rows, cols)
    thick = max(4, int(cell * 0.18))

    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * cell, y0 + r * cell
            sides, unassigned = parsed[r][c]
            pygame.draw.rect(surf, (250, 251, 253), (x, y, cell, cell))
            pygame.draw.rect(surf, theme.LINE, (x, y, cell, cell), 1)
            cx, cy = x + cell // 2, y + cell // 2

            if unassigned:
                theme.text(surf, fonts.sized(int(cell * 0.4)), "?", (190, 196, 205),
                           (cx, cy), "center")
            for d in sides:
                dr, dc, back = DIRS[d]
                nr, nc = r + dr, c + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    color = PIPE_BAD                       # hở ra ngoài biên
                else:
                    n_sides, n_unassigned = parsed[nr][nc]
                    if n_unassigned:
                        color = PIPE_PENDING
                    elif back in n_sides:
                        color = PIPE_OK
                    else:
                        color = PIPE_BAD
                ex = cx + dc * (cell // 2)
                ey = cy + dr * (cell // 2)
                pygame.draw.line(surf, color, (cx, cy), (ex, ey), thick)
            if sides:
                pygame.draw.circle(surf, PIPE_OK, (cx, cy), thick // 2 + 2)
            if (r, c) in changed:
                mark_changed(surf, x, y, cell)
