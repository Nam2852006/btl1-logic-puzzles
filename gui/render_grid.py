"""gui/render_grid.py - Vẽ lưới chung (dự phòng cho bài không có renderer riêng, vd N-Queens).
Người sở hữu: TV4.

Mọi renderer có cùng chữ ký:  draw(surf, rect, grid, changed, fonts)
  grid    : kết quả encode() của bài toán (list các list str/int)
  changed : tập (hàng, cột) có ô thay đổi so với bước trước (để tô viền vàng)
"""
from __future__ import annotations

import pygame

from gui import theme


def fit_cells(rect, rows, cols, pad=0):
    """Tính ô vuông lớn nhất đặt vừa trong rect, căn giữa. Trả về (x0, y0, cell)."""
    cell = max(8, min((rect.w - 2 * pad) // max(cols, 1), (rect.h - 2 * pad) // max(rows, 1)))
    x0 = rect.x + (rect.w - cell * cols) // 2
    y0 = rect.y + (rect.h - cell * rows) // 2
    return x0, y0, cell


def mark_changed(surf, x, y, cell):
    pygame.draw.rect(surf, theme.HILITE, (x, y, cell, cell), 3)


def draw(surf, rect, grid, changed, fonts):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if not rows or not cols:
        return
    x0, y0, cell = fit_cells(rect, rows, cols)
    font = fonts.sized(max(12, int(cell * 0.5)), bold=True)
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * cell, y0 + r * cell
            shade = (236, 239, 244) if (r + c) % 2 == 0 else (250, 251, 253)
            pygame.draw.rect(surf, shade, (x, y, cell, cell))
            v = str(grid[r][c])
            if v not in ("", "."):
                color = theme.ACCENT if v == "Q" else theme.INK
                theme.text(surf, font, v, color, (x + cell // 2, y + cell // 2), "center")
            pygame.draw.rect(surf, theme.LINE, (x, y, cell, cell), 1)
            if (r, c) in changed:
                mark_changed(surf, x, y, cell)
