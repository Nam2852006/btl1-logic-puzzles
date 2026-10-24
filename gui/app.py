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
    "expand": "Mở rộng một nút",
    "move": "Chuyển sang láng giềng tốt nhất",
    "restart": "Random restart (bắt đầu lại)",
    "result": "Kết quả cuối cùng",
}


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
            raise ValueError("file trace rỗng hoặc thiếu dòng meta")
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
    pygame.draw.rect(surf, (248, 249, 251), rect, border_radius=6)
    pygame.draw.rect(surf, theme.LINE, rect, 1, border_radius=6)
    hs = [f["h"] if isinstance(f["h"], (int, float)) else 0 for f in player.frames]
    lo, hi = min(hs), max(hs)
    span = (hi - lo) or 1
    w, h = rect.w - 16, rect.h - 24
    n = len(hs)

    def pt(i):
        return (rect.x + 8 + (i / max(n - 1, 1)) * w, rect.y + 8 + (1 - (hs[i] - lo) / span) * h)

    stride = max(1, n // max(w, 1))
    idxs = list(range(0, n, stride))
    for i in idxs:
        if player.frames[i]["event"] == "restart":
            x = pt(i)[0]
            pygame.draw.line(surf, (235, 200, 200), (x, rect.y + 6), (x, rect.bottom - 16), 1)
    if len(idxs) > 1:
        pygame.draw.lines(surf, theme.ACCENT, False, [pt(i) for i in idxs], 2)
    pygame.draw.circle(surf, theme.BAD, pt(player.idx), 5)
    text(surf, fonts.sized(12), f"h theo thời gian (min {lo:g}, max {hi:g})", theme.MUTED,
         (rect.x + 8, rect.bottom - 16))


def draw_panel(surf, player, fonts):
    pygame.draw.rect(surf, theme.PANEL, PANEL, border_radius=10)
    pygame.draw.rect(surf, theme.LINE, PANEL, 1, border_radius=10)
    m, f = player.meta, player.frames[player.idx]
    x, y = PANEL.x + 18, PANEL.y + 16

    text(surf, fonts.sized(24, True), player.title(), theme.INK, (x, y)); y += 34
    sub = f"{os.path.basename(str(m.get('input', '')))}  {m.get('size', '')}".strip()
    text(surf, fonts.sized(15), sub, theme.MUTED, (x, y)); y += 34

    rec = len([fr for fr in player.frames if fr["event"] != "result"])
    cur = player.idx + 1 if f["event"] != "result" else rec
    text(surf, fonts.sized(15), "Bước", theme.MUTED, (x, y))
    text(surf, fonts.sized(26, True), f"{cur} / {rec}", theme.INK, (x, y + 18))
    y += 62
    if m.get("truncated"):
        text(surf, fonts.sized(13), f"Trace đã cắt bớt: chỉ lưu {m.get('recorded_steps')} / "
             f"{m.get('total_steps')} bước", theme.WARN, (x, y)); y += 22

    text(surf, fonts.sized(15), "Sự kiện", theme.MUTED, (x, y))
    ev_color = theme.BAD if f["event"] == "restart" else (theme.GOOD if f["event"] == "result" else theme.INK)
    text(surf, fonts.sized(17, True), EVENT_LABEL.get(f["event"], f["event"]), ev_color, (x, y + 18))
    y += 54

    def stat(label, value, col, color=theme.INK):
        text(surf, fonts.sized(14), label, theme.MUTED, (x + col * 190, y))
        text(surf, fonts.sized(22, True), "-" if value is None else value, color, (x + col * 190, y + 18))

    prev_h = player.frames[player.idx - 1]["h"] if player.idx else None
    h_color = theme.INK
    if isinstance(f["h"], (int, float)) and isinstance(prev_h, (int, float)):
        h_color = theme.GOOD if f["h"] < prev_h else (theme.BAD if f["h"] > prev_h else theme.INK)
    stat("Giá trị h", f"{f['h']:g}" if isinstance(f["h"], (int, float)) else f["h"], 0, h_color)
    stat("Frontier", f["frontier"], 1)
    y += 56
    stat("Độ sâu", f["depth"], 0)
    nodes = f["step"] if f["step"] is not None else (player.result or {}).get("nodes_expanded")
    stat("Nút đã mở rộng", nodes, 1)
    y += 56
    if player.meta.get("algorithm") == "hc":
        stat("Số lần restart", player.restarts_upto[player.idx], 0)
        y += 56

    draw_sparkline(surf, pygame.Rect(PANEL.x + 14, y, PANEL.w - 28, 96), player, fonts)
    y += 108

    if player.idx >= player.n - 1 and player.result is not None:
        ok = player.result.get("success")
        color = theme.GOOD if ok else theme.BAD
        box = pygame.Rect(PANEL.x + 14, y, PANEL.w - 28, 56)
        pygame.draw.rect(surf, color, box, border_radius=8)
        msg = "TÌM THẤY LỜI GIẢI" if ok else "KHÔNG TÌM THẤY LỜI GIẢI"
        text(surf, fonts.sized(18, True), msg, (255, 255, 255), (box.centerx, box.y + 16), "midtop")
        extra = f"{player.result.get('nodes_expanded')} nút mở rộng"
        if player.meta.get("algorithm") == "hc":
            extra += f", {player.result.get('restarts')} restart"
        text(surf, fonts.sized(13), extra, (255, 255, 255), (box.centerx, box.y + 38), "midtop")


def make_buttons(player):
    labels = [("first", "|<"), ("prev", "<"), ("play", "Dừng" if player.playing else "Phát"),
              ("next", ">"), ("last", ">|"), ("slower", "-"), ("faster", "+"),
              ("shot", "Chụp ảnh"), ("menu", "Menu")]
    widths = {"play": 90, "shot": 110, "menu": 90}
    x, out = BAR.x, []
    for key, label in labels:
        w = widths.get(key, 56)
        if key == "slower":
            x += 24
        out.append((key, label, pygame.Rect(x, BAR.y + 10, w, 44)))
        x += w + 10
        if key == "faster":
            x += 24
    return out


def draw_bar(surf, player, fonts):
    pygame.draw.rect(surf, theme.PANEL, BAR, border_radius=10)
    pygame.draw.rect(surf, theme.LINE, BAR, 1, border_radius=10)
    for key, label, rect in make_buttons(player):
        main = key == "play"
        pygame.draw.rect(surf, theme.ACCENT if main else (238, 240, 244), rect, border_radius=8)
        text(surf, fonts.sized(17, True), label, (255, 255, 255) if main else theme.INK,
             rect.center, "center")
    text(surf, fonts.sized(15), "Tốc độ", theme.MUTED, (BAR.right - 20, BAR.y + 12), "topright")
    text(surf, fonts.sized(18, True), f"{SPEEDS[player.speed_i]} bước/giây", theme.INK,
         (BAR.right - 20, BAR.y + 32), "topright")


def draw_player(surf, player, fonts):
    surf.fill(theme.BG)
    pygame.draw.rect(surf, theme.PANEL, BOARD, border_radius=10)
    pygame.draw.rect(surf, theme.LINE, BOARD, 1, border_radius=10)
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
    surf.fill(theme.BG)
    text(surf, fonts.sized(30, True), "Demo tìm kiếm step-by-step", theme.INK, (40, 36))
    text(surf, fonts.sized(16), "Chọn một file trace (↑/↓ + Enter, hoặc bấm chuột). "
         "Tạo trace mới: python main.py ... --trace", theme.MUTED, (40, 80))
    if error:
        text(surf, fonts.sized(15), error, theme.BAD, (40, 104))
    pygame.draw.rect(surf, theme.PANEL, MENU_LIST, border_radius=10)
    pygame.draw.rect(surf, theme.LINE, MENU_LIST, 1, border_radius=10)
    if not items:
        text(surf, fonts.sized(18), "Chưa có file trace nào trong results/traces/ hoặc gui/demo_traces/.",
             theme.MUTED, MENU_LIST.center, "center")
        return
    clip = surf.get_clip()
    surf.set_clip(MENU_LIST)
    for i, (path, meta) in enumerate(items):
        row = pygame.Rect(MENU_LIST.x + 6, MENU_LIST.y + 6 + (i - scroll) * ROW_H, MENU_LIST.w - 12, ROW_H - 4)
        if i == sel:
            pygame.draw.rect(surf, (225, 235, 255), row, border_radius=8)
        label = (f"{PUZZLE_NAME.get(meta.get('puzzle'), meta.get('puzzle'))}  -  "
                 f"{ALGO_NAME.get(meta.get('algorithm'), meta.get('algorithm'))}")
        text(surf, fonts.sized(18, True), label, theme.INK, (row.x + 14, row.centery), "midleft")
        info = (f"{os.path.basename(str(meta.get('input', '')))}   {meta.get('size', '')}   "
                f"{meta.get('recorded_steps', '?')} bước" + ("  (đã cắt)" if meta.get("truncated") else ""))
        text(surf, fonts.sized(15), info, theme.MUTED, (row.x + 360, row.centery), "midleft")
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
    pygame.display.set_caption("BTL1 - Demo tìm kiếm step-by-step")
    fonts = Fonts()
    clock = pygame.time.Clock()

    player, error = None, ""
    items, sel, scroll = scan_traces(), 0, 0
    if initial:
        try:
            player = Player(initial)
        except Exception as e:  # noqa: BLE001 - hiển thị lỗi thay vì sập
            error = f"Không mở được {initial}: {e}"

    def open_item(i):
        nonlocal player, error
        try:
            player = Player(items[i][0])
            error = ""
        except Exception as e:  # noqa: BLE001
            error = f"Không mở được {os.path.basename(items[i][0])}: {e}"

    def press(key):
        if key == "first": player.goto(0)
        elif key == "prev": player.goto(player.idx - 1)
        elif key == "next": player.goto(player.idx + 1)
        elif key == "last": player.goto(player.n - 1)
        elif key == "play": player.toggle()
        elif key == "slower": player.speed_i = max(0, player.speed_i - 1)
        elif key == "faster": player.speed_i = min(len(SPEEDS) - 1, player.speed_i + 1)
        elif key == "shot":
            print("Đã lưu ảnh:", save_screenshot(screen, player))
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
        print("Đã lưu ảnh:", save_screenshot(screen, player, args.screenshot))
        return
    run_gui(args.trace)


if __name__ == "__main__":
    main()
