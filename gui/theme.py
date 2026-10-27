"""gui/theme.py - Bảng màu kiểu hoạt hình và các hàm vẽ dùng chung. Người sở hữu: TV4.

Phong cách: nền trời xanh có mây, khung dày viền đậm có bóng đổ, nút nổi 3D, chữ có viền.
Mọi hình đều tự vẽ bằng pygame (không dùng ảnh ngoài).
"""
from __future__ import annotations

import math

import pygame

# ----- Bảng màu -----
OUTLINE = (52, 36, 77)          # viền tím than đậm, dùng cho mọi khối
SKY_TOP = (84, 176, 255)
SKY_BOT = (196, 234, 255)
CREAM = (255, 246, 214)         # nền các khung
CREAM_DARK = (236, 214, 160)
INK = (62, 40, 30)              # chữ chính: nâu đậm
MUTED = (140, 104, 74)          # chữ phụ
WHITE = (255, 255, 255)
YELLOW = (255, 204, 40)
ORANGE = (255, 146, 40)
RED = (238, 72, 62)
GREEN = (72, 196, 84)
GREEN_DARK = (28, 112, 52)
GREEN_LIGHT = (150, 232, 130)
BLUE = (66, 140, 240)
BROWN = (150, 92, 52)
BRICK = (214, 118, 66)

# Tên cũ, giữ lại để các file khác dùng chung
BG = SKY_BOT
PANEL = CREAM
LINE = CREAM_DARK
ACCENT = BLUE
GOOD = (30, 160, 60)
BAD = (222, 50, 44)
WARN = (214, 120, 0)
HILITE = YELLOW


def darker(color, k=0.55):
    return tuple(int(v * k) for v in color)


def lighter(color, k=0.45):
    return tuple(int(v + (255 - v) * k) for v in color)


class Fonts:
    """Cache font theo cỡ chữ. Dò từng font trong danh sách và chỉ chọn font có ĐỦ chữ tiếng Việt
    (kể cả dấu kép như ể, ộ, ơ, ư), vì nhiều font đẹp như Trebuchet/Comic Sans thiếu các chữ này."""

    CANDIDATES = ["segoeui", "tahoma", "arial", "verdana", "calibri", "dejavusans",
                  "freesans", "liberationsans", "notosans", "inter"]
    PROBE = "ắặằẳẵấầẩẫậếềểễệốồổỗộớờởỡợứừửữựỳỷỹỵđĐơưƠƯ"

    def __init__(self):
        self._cache = {}
        self._name = None

    def _pick(self):
        """Tên font đầu tiên có đủ glyph tiếng Việt; None nếu không có (dùng font mặc định)."""
        if self._name is None:
            self._name = ""
            for name in self.CANDIDATES:
                try:
                    path = pygame.font.match_font(name)
                    if not path:
                        continue
                    font = pygame.font.Font(path, 20)
                    if all(m is not None for m in font.metrics(self.PROBE)):
                        self._name = name
                        break
                except (pygame.error, OSError, ValueError):
                    continue
        return self._name

    def sized(self, px: int, bold: bool = False) -> pygame.font.Font:
        key = (int(px), bold)
        if key not in self._cache:
            name = self._pick()
            self._cache[key] = (pygame.font.SysFont(name, int(px), bold=bold) if name
                                else pygame.font.Font(None, int(px * 1.2)))
        return self._cache[key]


def text(surf, font, s, color, pos, anchor="topleft", outline=None, ow=2):
    """Vẽ chuỗi s tại pos, neo theo anchor. outline=(r,g,b) thì viền chữ dày ow px. Trả về Rect."""
    s = str(s)
    img = font.render(s, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    if outline is not None:
        edge = font.render(s, True, outline)
        for dx in range(-ow, ow + 1):
            for dy in range(-ow, ow + 1):
                if dx * dx + dy * dy <= ow * ow + 1:
                    surf.blit(edge, rect.move(dx, dy))
    surf.blit(img, rect)
    return rect


def block(surf, rect, fill, radius=14, width=3, shadow=5):
    """Khối bo góc: bóng đổ phía dưới, nền, viền đậm."""
    rect = pygame.Rect(rect)
    if shadow:
        pygame.draw.rect(surf, darker(fill, 0.5), rect.move(0, shadow), border_radius=radius)
    pygame.draw.rect(surf, fill, rect, border_radius=radius)
    pygame.draw.rect(surf, OUTLINE, rect, width, border_radius=radius)
    if shadow:   # viền bóng đổ
        pygame.draw.line(surf, OUTLINE, (rect.x + radius, rect.bottom + shadow - 1),
                         (rect.right - radius, rect.bottom + shadow - 1), width)


def button(surf, rect, fill, label, font, hover=False, label_color=WHITE):
    """Nút nổi 3D: bấm/di chuột vào thì lún xuống."""
    rect = pygame.Rect(rect)
    lift = 2 if hover else 5
    top = rect.move(0, 5 - lift)
    base = lighter(fill, 0.18) if hover else fill
    pygame.draw.rect(surf, OUTLINE, rect.move(0, 5), border_radius=12)
    pygame.draw.rect(surf, darker(fill, 0.62), rect.move(0, 5).inflate(-4, -4), border_radius=10)
    pygame.draw.rect(surf, base, top, border_radius=12)
    pygame.draw.rect(surf, OUTLINE, top, 3, border_radius=12)
    shine = pygame.Rect(top.x + 8, top.y + 5, top.w - 16, max(4, top.h // 5))
    pygame.draw.rect(surf, lighter(base, 0.45), shine, border_radius=4)
    text(surf, font, label, label_color, top.center, "center", outline=OUTLINE, ow=2)


def star(surf, center, r, fill=YELLOW):
    cx, cy = center
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    pygame.draw.polygon(surf, fill, pts)
    pygame.draw.polygon(surf, OUTLINE, pts, 3)


# ----- Nền trời có mây và đồi cỏ (vẽ một lần rồi cache) -----
_SKY_CACHE = {}


def _cloud(surf, x, y, s):
    parts = [(0, 0, 34), (36, -12, 42), (80, 0, 34), (40, 10, 34)]
    for dx, dy, r in parts:
        pygame.draw.circle(surf, OUTLINE, (x + int(dx * s), y + int(dy * s)), int(r * s) + 3)
    for dx, dy, r in parts:
        pygame.draw.circle(surf, WHITE, (x + int(dx * s), y + int(dy * s)), int(r * s))


def sky(surf):
    """Vẽ nền lên toàn bộ surf."""
    size = surf.get_size()
    if size not in _SKY_CACHE:
        w, h = size
        bg = pygame.Surface(size)
        for y in range(h):
            t = y / max(h - 1, 1)
            col = tuple(int(SKY_TOP[i] + (SKY_BOT[i] - SKY_TOP[i]) * t) for i in range(3))
            pygame.draw.line(bg, col, (0, y), (w, y))
        for x, y, s in [(60, 40, 0.8), (520, 12, 0.7), (930, 52, 0.9), (1090, 300, 0.6), (40, 560, 0.7)]:
            _cloud(bg, x, y, s)
        # đồi cỏ phía dưới
        pts = [(0, h)]
        for x in range(0, w + 20, 20):
            pts.append((x, h - 34 + int(10 * math.sin(x / 70.0))))
        pts.append((w, h))
        pygame.draw.polygon(bg, GREEN, pts)
        pygame.draw.lines(bg, GREEN_DARK, False, pts[1:-1], 4)
        _SKY_CACHE[size] = bg
    surf.blit(_SKY_CACHE[size], (0, 0))
