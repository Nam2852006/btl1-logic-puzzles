"""gui/theme.py - Màu sắc, font và hàm vẽ chữ dùng chung. Người sở hữu: TV4."""
from __future__ import annotations

import pygame

BG = (244, 245, 247)
PANEL = (255, 255, 255)
INK = (30, 34, 40)
MUTED = (120, 128, 140)
LINE = (210, 214, 220)
ACCENT = (37, 99, 235)
GOOD = (22, 163, 74)
BAD = (220, 38, 38)
WARN = (234, 138, 0)
HILITE = (255, 196, 0)


class Fonts:
    """Cache font theo cỡ chữ. Thử lần lượt các font có hỗ trợ tiếng Việt."""

    NAMES = "segoeui,arial,helvetica,dejavusans,freesans"

    def __init__(self):
        self._cache = {}

    def sized(self, px: int, bold: bool = False) -> pygame.font.Font:
        key = (int(px), bold)
        if key not in self._cache:
            self._cache[key] = pygame.font.SysFont(self.NAMES, int(px), bold=bold)
        return self._cache[key]


def text(surf, font, s, color, pos, anchor="topleft"):
    """Vẽ chuỗi s tại pos, neo theo anchor (topleft, center, midright...). Trả về Rect."""
    img = font.render(str(s), True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    surf.blit(img, rect)
    return rect
