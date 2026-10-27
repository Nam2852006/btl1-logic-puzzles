"""gui/app.py - Ứng dụng pygame phát lại từng bước tìm kiếm. Người sở hữu: TV4.

GUI CHỈ ĐỌC file trace (.jsonl) do TV1 xuất, không gọi giải thuật. Tạo trace bằng:
    python main.py --puzzle tents --algo astar --input inputs/tents/01.txt --trace

Chạy:
    python gui/app.py                          # menu chọn trace trong results/traces/
    python gui/app.py results/traces/x.jsonl   # mở thẳng một trace
    python gui/app.py x.jsonl --step 7 --screenshot anh.png   # chụp một bước, không mở cửa sổ

Phím: Space phát/dừng | ←/→ lùi/tiến 1 bước | ↑/↓ tăng/giảm tốc độ | Home/End về đầu/cuối
      S chụp ảnh (results/screenshots/) | Esc về menu (ở menu: thoát)
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from core.tracer import load_trace  # noqa: E402
from gui import render_grid, render_pipes, render_tents, theme  # noqa: E402
from gui.theme import Fonts, text  # noqa: E402

WIN_W, WIN_H = 1180, 740
BOARD = pygame.Rect(20, 20, 720, 620)
PANEL = pygame.Rect(760, 20, 400, 620)
BAR = pygame.Rect(20, 656, 1140, 64)
SPEEDS = [1, 2, 5, 10, 20, 50, 100, 200, 500]   # bước / giây
TRACE_DIRS = [os.path.join(ROOT, "results", "traces"), os.path.join(ROOT, "gui", "demo_traces")]

RENDERERS = {"pipes": render_pipes, "tents": render_tents}
PUZZLE_NAME = {"pipes": "Pipes", "tents": "Tents", "nqueens": "N-Queens"}
ALGO_NAME = {"dfs": "DFS", "bfs": "BrFS", "astar": "A*", "hc": "Hill Climbing"}
EVENT_LABEL = {
    "start": "Start state",
    "expand": "Expand a node",
    "move": "Move to best neighbor",
    "restart": "Random restart",
    "result": "Final result",
}


def _finite(h):
    """Giá trị h là số hữu hạn -> trả về số đó. Ngõ cụt ("inf" hoặc Infinity) hay thiếu -> None."""
    if isinstance(h, (int, float)) and math.isfinite(h):
        return h
    return None


def _is_dead_end(h):
    """h = vô cùng: trạng thái ngõ cụt (vd. heuristic tension của Tents)."""
    return h == "inf" or (isinstance(h, float) and math.isinf(h))


# ----------------------------------------------------------------------
# Dữ liệu phát lại
# ----------------------------------------------------------------------
class Player:
    """Giữ trace đã nạp và vị trí bước hiện tại."""

    def __init__(self, path):
        self.path = path
        self.meta, steps, self.result = load_trace(path)
        self.frames = [dict(step=s["step"], event=s.get("event", "expand"), grid=s["grid"],
                            h=s.get("h"), frontier=s.get("frontier"), depth=s.get("depth"))
                       for s in steps]
        if self.result and self.result.get("success") and self.result.get("grid"):
            self.frames.append(dict(step=None, event="result", grid=self.result["grid"],
                                    h=0, frontier=None, depth=None))
        if not self.frames or self.meta is None:
            raise ValueError("empty trace file or missing meta line")
        self.idx = 0
        self.playing = False
        self.speed_i = 3
        self._acc = 0.0
        self.restarts_upto, n = [], 0
        for f in self.frames:
            n += f["event"] == "restart"
            self.restarts_upto.append(n)

    @property
    def n(self):
        return len(self.frames)

    def goto(self, i):
        self.idx = max(0, min(self.n - 1, i))

    def update(self, dt):
        if not self.playing:
            return
        self._acc += dt * SPEEDS[self.speed_i]
        k = int(self._acc)
        self._acc -= k
        self.goto(self.idx + k)
        if self.idx >= self.n - 1:
            self.playing = False

    def toggle(self):
        if self.idx >= self.n - 1:
            self.idx = 0
        self.playing = not self.playing

    def changed_cells(self):
        if self.idx == 0:
            return set()
        a, b = self.frames[self.idx - 1]["grid"], self.frames[self.idx]["grid"]
        if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
            return set()
        return {(r, c) for r in range(len(b)) for c in range(len(b[r])) if a[r][c] != b[r][c]}

    def title(self):
        m = self.meta
        return f"{PUZZLE_NAME.get(m.get('puzzle'), m.get('puzzle'))} - {ALGO_NAME.get(m.get('algorithm'), m.get('algorithm'))}"


# ----------------------------------------------------------------------
# Vẽ màn hình phát lại
# ----------------------------------------------------------------------
def draw_sparkline(surf, rect, player, fonts):
    theme.block(surf, rect, (255, 252, 238), radius=10, width=3, shadow=0)
    vals = [_finite(f["h"]) for f in player.frames]
    finite = [v for v in vals if v is not None]
    lo, hi = (min(finite), max(finite)) if finite else (0, 0)
    hs = [hi if v is None else v for v in vals]      # ngõ cụt / thiếu h: vẽ ở đỉnh biểu đồ
    span = (hi - lo) or 1
    w, h = rect.w - 24, rect.h - 38
    n = len(hs)

    def pt(i):
        return (rect.x + 12 + (i / max(n - 1, 1)) * w, rect.y + 10 + (1 - (hs[i] - lo) / span) * h)

    stride = max(1, n // max(w, 1))
    idxs = list(range(0, n, stride))
    for i in idxs:
        if player.frames[i]["event"] == "restart":
            x = pt(i)[0]
            pygame.draw.line(surf, (240, 150, 140), (x, rect.y + 8), (x, rect.bottom - 24), 2)
    if len(idxs) > 1:
        pts = [pt(i) for i in idxs]
        pygame.draw.lines(surf, theme.OUTLINE, False, pts, 7)
        pygame.draw.lines(surf, theme.BLUE, False, pts, 4)
    cx, cy = pt(player.idx)
    pygame.draw.circle(surf, theme.OUTLINE, (cx, cy), 9)
    pygame.draw.circle(surf, theme.YELLOW, (cx, cy), 6)
    text(surf, fonts.sized(13), f"h over time (min {lo:g}, max {hi:g})", theme.MUTED,
         (rect.x + 12, rect.bottom - 22))


def draw_progress(surf, rect, frac):
    """Thanh tiến độ kiểu màn chơi: chạy từ trái sang phải, có ngôi sao ở đích."""
    theme.block(surf, rect, (255, 252, 238), radius=rect.h // 2, width=3, shadow=0)
    inner = rect.inflate(-8, -8)
    fill = pygame.Rect(inner.x, inner.y, int((inner.w - inner.h) * frac) + inner.h, inner.h)
    pygame.draw.rect(surf, theme.GREEN, fill, border_radius=inner.h // 2)
    pygame.draw.rect(surf, theme.GREEN_LIGHT, fill.inflate(-8, -inner.h // 2), border_radius=3)
    theme.star(surf, (rect.right - 2, rect.centery), rect.h * 0.9,
               theme.YELLOW if frac >= 1 else (214, 200, 150))


def draw_panel(surf, player, fonts):
    theme.block(surf, PANEL, theme.CREAM, radius=16, width=4, shadow=6)
    m, f = player.meta, player.frames[player.idx]

    banner = pygame.Rect(PANEL.x, PANEL.y, PANEL.w, 74)
    pygame.draw.rect(surf, theme.RED, banner, border_top_left_radius=16, border_top_right_radius=16)
    pygame.draw.rect(surf, theme.lighter(theme.RED, 0.35),
                     pygame.Rect(banner.x + 10, banner.y + 6, banner.w - 20, 8), border_radius=4)
    pygame.draw.line(surf, theme.OUTLINE, (banner.x, banner.bottom), (banner.right, banner.bottom), 4)
    pygame.draw.rect(surf, theme.OUTLINE, PANEL, 4, border_radius=16)
    text(surf, fonts.sized(26, True), player.title(), theme.WHITE, (banner.centerx, banner.y + 24),
         "center", outline=theme.OUTLINE, ow=3)
    sub = f"{os.path.basename(str(m.get('input', '')))}  {m.get('size', '')}".strip()
    text(surf, fonts.sized(15, True), sub, theme.WHITE, (banner.centerx, banner.y + 54),
         "center", outline=theme.OUTLINE, ow=2)

    x, y = PANEL.x + 20, PANEL.y + 88
    rec = len([fr for fr in player.frames if fr["event"] != "result"])
    cur = player.idx + 1 if f["event"] != "result" else rec
    text(surf, fonts.sized(15, True), "STEP", theme.MUTED, (x, y))
    text(surf, fonts.sized(28, True), f"{cur} / {rec}", theme.INK, (x, y + 16))
    draw_progress(surf, pygame.Rect(x + 130, y + 24, PANEL.w - 40 - 130 - 18, 22),
                  player.idx / max(player.n - 1, 1))
    y += 58
    if m.get("truncated"):
        text(surf, fonts.sized(13, True), f"Trace truncated: only {m.get('recorded_steps')} / "
             f"{m.get('total_steps')} steps saved", theme.WARN, (x, y)); y += 22

    text(surf, fonts.sized(15, True), "EVENT", theme.MUTED, (x, y))
    ev_color = theme.BAD if f["event"] == "restart" else (theme.GOOD if f["event"] == "result" else theme.INK)
    text(surf, fonts.sized(18, True), EVENT_LABEL.get(f["event"], f["event"]), ev_color, (x, y + 18))
    y += 52

    def stat(label, value, col, color=theme.INK):
        text(surf, fonts.sized(14, True), label.upper(), theme.MUTED, (x + col * 188, y))
        text(surf, fonts.sized(22, True), "-" if value is None else value, color, (x + col * 188, y + 18))

    cur_h = _finite(f["h"])
    prev_h = _finite(player.frames[player.idx - 1]["h"]) if player.idx else None
    h_color = theme.INK
    if cur_h is not None and prev_h is not None:
        h_color = theme.GOOD if cur_h < prev_h else (theme.BAD if cur_h > prev_h else theme.INK)
    if cur_h is not None:
        h_text = f"{cur_h:g}"
    elif _is_dead_end(f["h"]):
        h_text, h_color = "dead end (inf)", theme.BAD
    else:
        h_text = None
    stat("h value", h_text, 0, h_color)
    stat("Frontier", f["frontier"], 1)
    y += 54
    stat("Depth", f["depth"], 0)
    nodes = f["step"] if f["step"] is not None else (player.result or {}).get("nodes_expanded")
    stat("Nodes expanded", nodes, 1)
    y += 54
    if player.meta.get("algorithm") == "hc":
        stat("Restarts", player.restarts_upto[player.idx], 0)
        y += 54

    draw_sparkline(surf, pygame.Rect(PANEL.x + 16, y, PANEL.w - 32, 92), player, fonts)
    y += 104

    if player.idx >= player.n - 1 and player.result is not None:
        ok = player.result.get("success")
        box = pygame.Rect(PANEL.x + 16, y, PANEL.w - 32, 58)
        theme.block(surf, box, theme.GREEN if ok else theme.RED, radius=12, width=3, shadow=4)
        msg = "SOLUTION FOUND!" if ok else "NO SOLUTION FOUND"
        text(surf, fonts.sized(19, True), msg, theme.WHITE, (box.centerx, box.y + 18), "center",
             outline=theme.OUTLINE, ow=3)
        extra = f"{player.result.get('nodes_expanded')} nodes expanded"
        if player.meta.get("algorithm") == "hc":
            extra += f", {player.result.get('restarts')} restart"
        text(surf, fonts.sized(13, True), extra, theme.WHITE, (box.centerx, box.y + 42), "center",
             outline=theme.OUTLINE, ow=2)
        if ok:
            theme.star(surf, (box.x + 4, box.y + 4), 15)
            theme.star(surf, (box.right - 4, box.y + 4), 15)


BTN_COLORS = {"play": theme.GREEN, "slower": theme.ORANGE, "faster": theme.ORANGE,
              "shot": theme.BLUE, "menu": theme.RED}


def make_buttons(player):
    labels = [("first", "|<"), ("prev", "<"), ("play", "Pause" if player.playing else "Play"),
              ("next", ">"), ("last", ">|"), ("slower", "-"), ("faster", "+"),
              ("shot", "Snapshot"), ("menu", "Menu")]
    widths = {"play": 90, "shot": 110, "menu": 90}
    x, out = BAR.x + 8, []
    for key, label in labels:
        w = widths.get(key, 56)
        if key == "slower":
            x += 24
        out.append((key, label, pygame.Rect(x, BAR.y + 8, w, 40)))
        x += w + 12
        if key == "faster":
            x += 24
    return out


def draw_bar(surf, player, fonts):
    theme.block(surf, BAR, theme.CREAM, radius=16, width=4, shadow=5)
    mouse = pygame.mouse.get_pos()
    for key, label, rect in make_buttons(player):
        theme.button(surf, rect, BTN_COLORS.get(key, (150, 130, 190)), label, fonts.sized(17, True),
                     hover=rect.collidepoint(mouse))
    text(surf, fonts.sized(14, True), "SPEED", theme.MUTED, (BAR.right - 20, BAR.y + 8), "topright")
    text(surf, fonts.sized(18, True), f"{SPEEDS[player.speed_i]} steps/s", theme.INK,
         (BAR.right - 20, BAR.y + 26), "topright")


def draw_player(surf, player, fonts):
    theme.sky(surf)
    theme.block(surf, BOARD, theme.CREAM, radius=16, width=4, shadow=6)
    renderer = RENDERERS.get(player.meta.get("puzzle"), render_grid)
    renderer.draw(surf, BOARD.inflate(-32, -32), player.frames[player.idx]["grid"],
                  player.changed_cells(), fonts)
    draw_panel(surf, player, fonts)
    draw_bar(surf, player, fonts)


def save_screenshot(surf, player, path=None):
    if path is None:
        base = os.path.splitext(os.path.basename(player.path))[0]
        path = os.path.join(ROOT, "results", "screenshots", f"{base}_step{player.idx + 1}.png")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pygame.image.save(surf, path)
    return path


# ----------------------------------------------------------------------
# Menu chọn trace (chọn bài / giải thuật / input)
# ----------------------------------------------------------------------
def scan_traces():
    items = []
    for d in TRACE_DIRS:
        for path in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            try:
                with open(path, encoding="utf-8") as fh:
                    meta = json.loads(fh.readline())
                if meta.get("type") != "meta":
                    continue
            except (OSError, ValueError):
                continue
            items.append((path, meta))
    order = {"pipes": 0, "tents": 1}
    items.sort(key=lambda it: (order.get(it[1].get("puzzle"), 9), it[1].get("puzzle", ""),
                               it[1].get("algorithm", ""), it[0]))
    return items


ROW_H = 44
MENU_LIST = pygame.Rect(40, 130, WIN_W - 80, WIN_H - 190)


def draw_menu(surf, items, sel, scroll, fonts, error):
    theme.sky(surf)
    text(surf, fonts.sized(38, True), "Step-by-step Search Demo", theme.YELLOW, (40, 30),
         outline=theme.OUTLINE, ow=4)
    text(surf, fonts.sized(16, True), "Pick a level (Up/Down keys + Enter, or click).  "
         "Make new traces: python main.py ... --trace", theme.INK, (40, 86))
    if error:
        text(surf, fonts.sized(15, True), error, theme.BAD, (40, 108))
    theme.block(surf, MENU_LIST, theme.CREAM, radius=16, width=4, shadow=6)
    if not items:
        text(surf, fonts.sized(18, True), "No trace files in results/traces/ or gui/demo_traces/.",
             theme.MUTED, MENU_LIST.center, "center")
        return
    clip = surf.get_clip()
    surf.set_clip(MENU_LIST.inflate(-8, -8))
    for i, (path, meta) in enumerate(items):
        row = pygame.Rect(MENU_LIST.x + 12, MENU_LIST.y + 10 + (i - scroll) * ROW_H,
                          MENU_LIST.w - 24, ROW_H - 6)
        if i == sel:
            theme.block(surf, row, theme.YELLOW, radius=10, width=3, shadow=0)
            theme.star(surf, (row.x + 22, row.centery), 12)
        else:
            pygame.draw.rect(surf, (255, 238, 196) if i % 2 == 0 else (250, 228, 176), row, border_radius=10)
        label = (f"{PUZZLE_NAME.get(meta.get('puzzle'), meta.get('puzzle'))}  -  "
                 f"{ALGO_NAME.get(meta.get('algorithm'), meta.get('algorithm'))}")
        text(surf, fonts.sized(18, True), label, theme.INK, (row.x + 46, row.centery), "midleft")
        info = (f"{os.path.basename(str(meta.get('input', '')))}   {meta.get('size', '')}   "
                f"{meta.get('recorded_steps', '?')} steps" + ("  (truncated)" if meta.get("truncated") else ""))
        text(surf, fonts.sized(15, True), info, theme.MUTED, (row.x + 390, row.centery), "midleft")
    surf.set_clip(clip)


def menu_visible_rows():
    return (MENU_LIST.h - 12) // ROW_H


# ----------------------------------------------------------------------
# Vòng lặp chính
# ----------------------------------------------------------------------
def run_gui(initial=None):
    pygame.init()
    pygame.key.set_repeat(300, 50)
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("BTL1 - Step-by-step Search Demo")
    fonts = Fonts()
    clock = pygame.time.Clock()

    player, error = None, ""
    items, sel, scroll = scan_traces(), 0, 0
    if initial:
        try:
            player = Player(initial)
        except Exception as e:  # noqa: BLE001 - hiển thị lỗi thay vì sập
            error = f"Cannot open {initial}: {e}"

    def open_item(i):
        nonlocal player, error
        try:
            player = Player(items[i][0])
            error = ""
        except Exception as e:  # noqa: BLE001
            error = f"Cannot open {os.path.basename(items[i][0])}: {e}"

    def press(key):
        if key == "first": player.goto(0)
        elif key == "prev": player.goto(player.idx - 1)
        elif key == "next": player.goto(player.idx + 1)
        elif key == "last": player.goto(player.n - 1)
        elif key == "play": player.toggle()
        elif key == "slower": player.speed_i = max(0, player.speed_i - 1)
        elif key == "faster": player.speed_i = min(len(SPEEDS) - 1, player.speed_i + 1)
        elif key == "shot":
            print("Saved screenshot:", save_screenshot(screen, player))
        elif key == "menu":
            return "menu"
        return None

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif player is None:                                   # --- menu
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                    elif ev.key == pygame.K_DOWN and items:
                        sel = min(len(items) - 1, sel + 1)
                    elif ev.key == pygame.K_UP and items:
                        sel = max(0, sel - 1)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and items:
                        open_item(sel)
                    rows = menu_visible_rows()
                    scroll = min(max(scroll, sel - rows + 1), sel)
                elif ev.type == pygame.MOUSEWHEEL:
                    scroll = max(0, min(max(0, len(items) - menu_visible_rows()), scroll - ev.y))
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and MENU_LIST.collidepoint(ev.pos):
                    i = scroll + (ev.pos[1] - MENU_LIST.y - 6) // ROW_H
                    if 0 <= i < len(items):
                        sel = i
                        open_item(i)
            else:                                                   # --- phát lại
                if ev.type == pygame.KEYDOWN:
                    k = {pygame.K_SPACE: "play", pygame.K_RIGHT: "next", pygame.K_LEFT: "prev",
                         pygame.K_UP: "faster", pygame.K_DOWN: "slower", pygame.K_HOME: "first",
                         pygame.K_END: "last", pygame.K_s: "shot", pygame.K_ESCAPE: "menu"}.get(ev.key)
                    if k and press(k) == "menu":
                        player, items = None, scan_traces()
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for key, _, rect in make_buttons(player):
                        if rect.collidepoint(ev.pos):
                            if press(key) == "menu":
                                player, items = None, scan_traces()
                            break
        if player is not None:
            player.update(dt)
            draw_player(screen, player, fonts)
        else:
            draw_menu(screen, items, sel, scroll, fonts, error)
        pygame.display.flip()
    pygame.quit()


def main():
    ap = argparse.ArgumentParser(description="GUI phát lại trace tìm kiếm (TV4)")
    ap.add_argument("trace", nargs="?", help="file .jsonl; bỏ trống để hiện menu")
    ap.add_argument("--screenshot", help="chụp một bước ra file PNG rồi thoát (không mở cửa sổ)")
    ap.add_argument("--step", type=int, default=0, help="bước cần chụp (bắt đầu từ 1; mặc định bước cuối)")
    args = ap.parse_args()

    if args.screenshot:
        if not args.trace:
            ap.error("--screenshot cần chỉ rõ file trace")
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        screen = pygame.display.set_mode((WIN_W, WIN_H))
        player = Player(args.trace)
        player.goto(args.step - 1 if args.step else player.n - 1)
        draw_player(screen, player, Fonts())
        print("Saved screenshot:", save_screenshot(screen, player, args.screenshot))
        return
    run_gui(args.trace)


if __name__ == "__main__":
    main()
