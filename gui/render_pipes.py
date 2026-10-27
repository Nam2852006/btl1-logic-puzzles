"""gui/render_pipes.py - Vẽ lưới Pipes. Người sở hữu: TV4.

QUY ƯỚC encode() của Pipes (theo puzzles/pipes.py của TV2, đã thống nhất):
  Mỗi ô là MỘT ký tự hex "0".."F" = bitmask các phía đang HỞ của ô ống sau khi xoay:
    Trên = 1, Phải = 2, Dưới = 4, Trái = 8.
    Ví dụ: "5" = 1+4 = ống thẳng đứng, "A" = 2+8 = ống thẳng ngang,
           "C" = 4+8 = ống cong dưới-trái, "D" = 1+4+8 = chữ T, "4" = đầu cụt quay xuống.
  "." = ô chưa gán (DFS gán dần từng ô). "?" cũng được hiểu là chưa gán.
Vì ô chứa sẵn các phía hở nên GUI không cần biết hình dạng gốc hay góc xoay.

Màu ống: xanh lá = phía hở khớp với láng giềng; đỏ = đầu hở không khớp (lỗi, h tăng);
vàng cam = láng giềng chưa gán nên chưa biết. Mỗi ống có viền đậm và vệt sáng cho giống hoạt hình.
"""
from __future__ import annotations

import pygame

from gui import theme
from gui.render_grid import fit_cells, mark_changed

DIRS = {"N": (-1, 0, "S"), "E": (0, 1, "W"), "S": (1, 0, "N"), "W": (0, -1, "E")}
PIPE_OK = theme.GREEN
PIPE_BAD = theme.RED
PIPE_PENDING = theme.ORANGE

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


def _segments(parsed, rows, cols):
    """Danh sách (hàng, cột, phía, màu) cho mọi đoạn ống."""
    segs = []
    for r in range(rows):
        for c in range(cols):
            sides, _ = parsed[r][c]
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
                segs.append((r, c, d, color))
    return segs


def draw(surf, rect, grid, changed, fonts):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if not rows or not cols:
        return
    parsed = [[parse_cell(v) for v in row] for row in grid]
    x0, y0, cell = fit_cells(rect, rows, cols)
    thick = max(6, int(cell * 0.26))
    rim = max(3, thick // 4)            # độ dày viền ống
    half = cell // 2

    def center(r, c):
        return x0 + c * cell + half, y0 + r * cell + half

    # nền ô: gạch sáng caro nhẹ
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * cell, y0 + r * cell
            pygame.draw.rect(surf, (255, 240, 200) if (r + c) % 2 == 0 else (250, 228, 182),
                             (x, y, cell, cell))
            if parsed[r][c][1]:
                theme.text(surf, fonts.sized(int(cell * 0.4), True), "?", (214, 184, 130),
                           (x + half, y + half), "center")
    pygame.draw.rect(surf, theme.OUTLINE, (x0, y0, cols * cell, rows * cell), 4)

    segs = _segments(parsed, rows, cols)
    # Vẽ theo 3 lượt trên TOÀN lưới để chỗ nối giữa các ô liền mạch, không bị viền cắt ngang.
    for r, c, d, color in segs:                                   # 1) viền
        cx, cy = center(r, c)
        dr, dc, _ = DIRS[d]
        pygame.draw.line(surf, theme.OUTLINE, (cx, cy), (cx + dc * half, cy + dr * half), thick + 2 * rim)
    for r in range(rows):
        for c in range(cols):
            if parsed[r][c][0]:
                pygame.draw.circle(surf, theme.OUTLINE, center(r, c), thick // 2 + rim + 2)
    for r, c, d, color in segs:                                   # 2) thân ống
        cx, cy = center(r, c)
        dr, dc, _ = DIRS[d]
        end = (cx + dc * half, cy + dr * half)
        pygame.draw.line(surf, color, (cx, cy), end, thick)
        sh = max(2, thick // 4)                                   # vệt sáng
        off = thick // 4
        pygame.draw.line(surf, theme.lighter(color, 0.55), (cx - off, cy - off),
                         (end[0] - off, end[1] - off), sh)
    for r in range(rows):                                         # 3) khớp nối ở giữa ô
        for c in range(cols):
            if parsed[r][c][0]:
                cx, cy = center(r, c)
                pygame.draw.circle(surf, PIPE_OK, (cx, cy), thick // 2 + 2)
                pygame.draw.circle(surf, theme.lighter(PIPE_OK, 0.55),
                                   (cx - thick // 5, cy - thick // 5), max(2, thick // 6))

    for (r, c) in changed:
        mark_changed(surf, x0 + c * cell, y0 + r * cell, cell)
