"""Bytewise - an isometric programming puzzle game.

Program the orange robot with command tiles to power up every beacon.
Run with: python main.py
"""
import json
import math
from pathlib import Path

import pygame

from engine import (ACTIVATE, CALLS, DIR_NAMES, FORWARD, JUMP, LEFT, PROGRAMS, RIGHT,
                    Interpreter, World, load_levels)

ROOT = Path(__file__).parent
SPRITE_DIR = ROOT / "assets" / "robot"
SAVE_FILE = ROOT / "save.json"

WIN_W, WIN_H = 1200, 760         # logical size; the window is SCALE times bigger
SCALE = 2
BOARD = pygame.Rect(0, 90, 720, 600)
PANEL_X = 735
TW, TH, BH = 72, 36, 18          # isometric tile width, tile height, block height
SLOT, GAP, COLS = 54, 8, 6
BASE_STEP = 0.45                  # seconds per instruction at 1x speed

BG_TOP = (22, 28, 52)
BG_BOTTOM = (54, 44, 86)
PANEL_BG = (30, 34, 58)
TEXT = (236, 238, 248)
MUTED = (150, 156, 186)
ACCENT = (255, 150, 50)
TILE_TOP = (176, 190, 214)
TILE_LEFT = (118, 130, 158)
TILE_RIGHT = (92, 102, 132)
PAD_OFF = (52, 84, 168)
PAD_OFF_EDGE = (120, 160, 255)
PAD_ON = (255, 220, 92)
PAD_ON_EDGE = (255, 250, 210)

CMD_COLORS = {
    FORWARD: (66, 133, 244), LEFT: (38, 166, 154), RIGHT: (38, 166, 154),
    JUMP: (156, 89, 210), ACTIVATE: (240, 150, 30), "P1": (76, 175, 80), "P2": (226, 84, 140),
}
PROG_LABELS = {"main": "MAIN", "p1": "P1", "p2": "P2"}


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    return t * t * (3 - 2 * t)


def shade(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)


def load_robot_sprites():
    if not all((SPRITE_DIR / f"robot_{n}.png").exists() for n in DIR_NAMES):
        import make_sprites
        make_sprites.main()
    sprites = [pygame.image.load(str(SPRITE_DIR / f"robot_{n}.png")).convert_alpha() for n in DIR_NAMES]
    meta = {}
    if (SPRITE_DIR / "sprite.json").exists():
        meta = json.loads((SPRITE_DIR / "sprite.json").read_text())
    scale = meta.get("scale", 1.0)
    if scale != 1.0:
        sprites = [pygame.transform.smoothscale(s, (round(s.get_width() * scale), round(s.get_height() * scale)))
                   for s in sprites]
    w, h = sprites[0].get_size()
    anchor = meta.get("anchor")
    anchor = (anchor[0] * scale, anchor[1] * scale) if anchor else (w / 2, h * 0.87)
    return sprites, anchor


def draw_icon(surf, cmd, rect, small=False):
    """Draw the white glyph for a command inside rect."""
    c = (255, 255, 255)
    cx, cy = rect.center
    s = rect.w / 54
    w = max(2, int(4 * s))
    if cmd == FORWARD:
        pygame.draw.line(surf, c, (cx, cy + 14 * s), (cx, cy - 6 * s), w + 1)
        pygame.draw.polygon(surf, c, [(cx, cy - 16 * s), (cx - 10 * s, cy - 4 * s), (cx + 10 * s, cy - 4 * s)])
    elif cmd in (LEFT, RIGHT):
        k = -1 if cmd == LEFT else 1
        x0 = cx - 6 * s * k
        pygame.draw.lines(surf, c, False, [(x0, cy + 15 * s), (x0, cy - 4 * s), (cx + 4 * s * k, cy - 4 * s)], w + 1)
        tip = cx + 14 * s * k
        pygame.draw.polygon(surf, c, [(tip, cy - 4 * s), (tip - 11 * s * k, cy - 14 * s), (tip - 11 * s * k, cy + 6 * s)])
    elif cmd == JUMP:
        arc = [(cx - 14 * s + i * 2.4 * s, cy + 12 * s - math.sin(i / 10 * math.pi) * 22 * s) for i in range(9)]
        pygame.draw.lines(surf, c, False, arc, w)
        pygame.draw.polygon(surf, c, [(cx + 14 * s, cy + 14 * s), (cx + 3 * s, cy + 5 * s), (cx + 15 * s, cy + 1 * s)])
        pygame.draw.line(surf, c, (cx - 18 * s, cy + 17 * s), (cx + 18 * s, cy + 17 * s), max(1, w - 1))
    elif cmd == ACTIVATE:
        pygame.draw.circle(surf, c, (cx, cy - 3 * s), 9 * s)
        pygame.draw.rect(surf, c, (cx - 5 * s, cy + 6 * s, 10 * s, 7 * s), border_radius=int(2 * s))
        for a in range(-2, 3):
            ang = math.radians(-90 + a * 40)
            p0 = (cx + math.cos(ang) * 13 * s, cy - 3 * s + math.sin(ang) * 13 * s)
            p1 = (cx + math.cos(ang) * 18 * s, cy - 3 * s + math.sin(ang) * 18 * s)
            pygame.draw.line(surf, c, p0, p1, max(1, w - 1))
    else:
        font = pygame.font.Font(None, int((26 if small else 34) * s))
        img = font.render(cmd, True, c)
        surf.blit(img, img.get_rect(center=rect.center))


def draw_tile_button(surf, cmd, rect, highlight=False, dim=False):
    color = CMD_COLORS[cmd]
    if dim:
        color = shade(color, 0.45)
    pygame.draw.rect(surf, shade(color, 0.6), rect.move(0, 3), border_radius=10)
    pygame.draw.rect(surf, color, rect, border_radius=10)
    pygame.draw.rect(surf, shade(color, 1.3), rect, 2, border_radius=10)
    draw_icon(surf, cmd, rect)
    if highlight:
        pygame.draw.rect(surf, (255, 240, 120), rect.inflate(6, 6), 3, border_radius=12)


class Button:
    def __init__(self, label, rect, action, color=(70, 78, 120)):
        self.label, self.rect, self.action, self.color = label, pygame.Rect(rect), action, color

    def draw(self, surf, font, mouse):
        hover = self.rect.collidepoint(mouse)
        col = shade(self.color, 1.2 if hover else 1.0)
        pygame.draw.rect(surf, shade(col, 0.6), self.rect.move(0, 3), border_radius=10)
        pygame.draw.rect(surf, col, self.rect, border_radius=10)
        img = font.render(self.label, True, TEXT)
        surf.blit(img, img.get_rect(center=self.rect.center))


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Bytewise")
        self.window = pygame.display.set_mode((WIN_W * SCALE, WIN_H * SCALE))
        self.screen = pygame.Surface((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 22)
        self.font_big = pygame.font.Font(None, 44)
        self.font_huge = pygame.font.Font(None, 64)
        self.sprites, self.anchor = load_robot_sprites()
        self.background = self.make_background()
        self.levels = load_levels()
        self.save = self.load_save()
        self.speed = 1
        self.time = 0.0
        self.show_levels = False
        self.drag = None
        self.load_level(min(self.save.get("current", 0), len(self.levels) - 1))

    # ---------- persistence ----------
    def load_save(self):
        try:
            return json.loads(SAVE_FILE.read_text())
        except (OSError, ValueError):
            return {}

    def write_save(self):
        self.save["current"] = self.level_index
        self.save.setdefault("programs", {})[str(self.level_index)] = self.programs
        try:
            SAVE_FILE.write_text(json.dumps(self.save, indent=1))
        except OSError:
            pass

    # ---------- level / run state ----------
    def load_level(self, index):
        self.level_index = index
        self.level = self.levels[index]
        saved = self.save.get("programs", {}).get(str(index), {})
        self.programs = {p: list(saved.get(p, [])) for p in PROGRAMS}
        self.selected = "main"
        self.reset_run()
        self.layout()
        self.compute_board_origin()

    def reset_run(self):
        self.world = World(self.level)
        self.interp = None
        self.running = False
        self.anim = None
        self.highlight = None
        self.result = None   # None | "win" | "fail" | "overflow"

    def start_run(self):
        self.reset_run()
        self.interp = Interpreter(self.programs)
        self.running = True

    def toggle_run(self):
        if self.running or self.result:
            self.reset_run()
        else:
            self.start_run()

    def visible_programs(self):
        return [p for p in PROGRAMS if self.level.limits[p] > 0]

    def palette(self):
        return [c for c in self.level.commands if c not in CALLS or self.level.limits[CALLS[c]] > 0]

    # ---------- layout ----------
    def layout(self):
        x = PANEL_X
        self.palette_rects = [(cmd, pygame.Rect(x + 12 + i * (SLOT + GAP), 52, SLOT, SLOT))
                              for i, cmd in enumerate(self.palette())]
        self.boxes = {}
        y = 140
        for prog in self.visible_programs():
            limit = self.level.limits[prog]
            rows = math.ceil(limit / COLS)
            box = pygame.Rect(x, y, COLS * (SLOT + GAP) + 16, 34 + rows * (SLOT + GAP) + 6)
            slots = [pygame.Rect(x + 12 + (i % COLS) * (SLOT + GAP), y + 34 + (i // COLS) * (SLOT + GAP), SLOT, SLOT)
                     for i in range(limit)]
            self.boxes[prog] = (box, slots)
            y = box.bottom + 14
        by = WIN_H - 70
        self.buttons = [
            Button("Run", (x, by, 120, 46), self.toggle_run, (46, 160, 90)),
            Button("Clear", (x + 132, by, 100, 46), self.clear_selected, (170, 70, 70)),
            Button(f"Speed {self.speed}x", (x + 244, by, 120, 46), self.cycle_speed),
        ]
        self.nav_buttons = [
            Button("< Prev", (20, WIN_H - 62, 100, 40), lambda: self.change_level(-1)),
            Button("Levels", (130, WIN_H - 62, 100, 40), self.open_levels),
            Button("Next >", (240, WIN_H - 62, 100, 40), lambda: self.change_level(1)),
        ]

    def compute_board_origin(self):
        xs, ys = [], []
        for (x, y), h in self.level.heights.items():
            sx, sy = (x - y) * TW / 2, (x + y) * TH / 2
            xs += [sx - TW / 2, sx + TW / 2]
            ys += [sy - h * BH - TH / 2 - 70, sy + TH / 2]
        self.ox = BOARD.centerx - (min(xs) + max(xs)) / 2
        self.oy = BOARD.centery - (min(ys) + max(ys)) / 2

    def iso(self, x, y, h):
        return self.ox + (x - y) * TW / 2, self.oy + (x + y) * TH / 2 - h * BH

    # ---------- actions ----------
    def clear_selected(self):
        self.programs[self.selected] = []
        self.on_edit()

    def cycle_speed(self):
        self.speed = {1: 2, 2: 4, 4: 1}[self.speed]
        self.buttons[2].label = f"Speed {self.speed}x"

    def change_level(self, delta):
        self.write_save()
        self.load_level((self.level_index + delta) % len(self.levels))

    def open_levels(self):
        self.show_levels = True

    def on_edit(self):
        if self.running or self.result:
            self.reset_run()
        self.write_save()

    def insert(self, prog, index, cmd):
        if len(self.programs[prog]) >= self.level.limits[prog]:
            return False
        self.programs[prog].insert(min(index, len(self.programs[prog])), cmd)
        return True

    # ---------- input ----------
    def hit_program(self, pos):
        """Return (prog, slot_index or None) under pos, or None."""
        for prog, (box, slots) in self.boxes.items():
            if box.collidepoint(pos):
                for i, r in enumerate(slots):
                    if r.collidepoint(pos):
                        return prog, i
                return prog, None
        return None

    def on_mouse_down(self, pos):
        if self.show_levels:
            for i, r in enumerate(self.level_grid_rects()):
                if r.collidepoint(pos):
                    self.show_levels = False
                    self.write_save()
                    self.load_level(i)
                    return
            self.show_levels = False
            return
        if self.result == "win" and self.overlay_next_rect().collidepoint(pos):
            self.change_level(1)
            return
        for b in self.buttons + self.nav_buttons:
            if b.rect.collidepoint(pos):
                b.action()
                return
        for cmd, r in self.palette_rects:
            if r.collidepoint(pos):
                self.drag = {"cmd": cmd, "src": None, "start": pos, "moved": False}
                return
        hit = self.hit_program(pos)
        if hit:
            prog, i = hit
            self.selected = prog
            if i is not None and i < len(self.programs[prog]):
                self.drag = {"cmd": self.programs[prog][i], "src": (prog, i), "start": pos, "moved": False}

    def on_mouse_move(self, pos):
        if self.drag and not self.drag["moved"]:
            sx, sy = self.drag["start"]
            if abs(pos[0] - sx) + abs(pos[1] - sy) > 6:
                self.drag["moved"] = True

    def on_mouse_up(self, pos):
        drag, self.drag = self.drag, None
        if not drag:
            return
        cmd, src = drag["cmd"], drag["src"]
        if not drag["moved"]:
            # click: palette appends to selected program, program tile is removed
            if src is None:
                self.insert(self.selected, 99, cmd)
            else:
                self.programs[src[0]].pop(src[1])
            self.on_edit()
            return
        hit = self.hit_program(pos)
        if src is not None:
            self.programs[src[0]].pop(src[1])
        if hit:
            prog, i = hit
            index = len(self.programs[prog]) if i is None else i
            if not self.insert(prog, index, cmd) and src is not None:
                self.programs[src[0]].insert(src[1], cmd)   # target full: put it back
            else:
                self.selected = prog
        self.on_edit()

    def on_key(self, key):
        if self.show_levels:
            if key == pygame.K_ESCAPE:
                self.show_levels = False
            return
        if key == pygame.K_SPACE:
            self.toggle_run()
        elif key == pygame.K_BACKSPACE and self.programs[self.selected]:
            self.programs[self.selected].pop()
            self.on_edit()
        elif key in (pygame.K_r, pygame.K_ESCAPE):
            self.reset_run()
        elif key == pygame.K_TAB:
            progs = self.visible_programs()
            self.selected = progs[(progs.index(self.selected) + 1) % len(progs)]
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.result == "win":
            self.change_level(1)
        else:
            keymap = {pygame.K_UP: FORWARD, pygame.K_LEFT: LEFT, pygame.K_RIGHT: RIGHT,
                      pygame.K_j: JUMP, pygame.K_a: ACTIVATE, pygame.K_1: "P1", pygame.K_2: "P2"}
            cmd = keymap.get(key)
            if cmd in self.palette():
                self.insert(self.selected, 99, cmd)
                self.on_edit()

    # ---------- simulation ----------
    def update(self, dt):
        self.time += dt
        if not self.running:
            return
        if self.anim:
            self.anim["t"] += dt * self.speed / self.anim["dur"]
            if self.anim["t"] < 1:
                return
            self.anim = None
            if self.world.won():
                self.finish("win")
                return
        nxt = self.interp.next()
        if nxt is None:
            self.finish("overflow" if self.interp.overflow else "fail")
            return
        prog, idx, cmd = nxt
        self.highlight = (prog, idx)
        w = self.world
        before = (w.x, w.y, w.h, w.d)
        if cmd in CALLS:
            self.anim = {"kind": "call", "t": 0.0, "dur": BASE_STEP * 0.3, "from": before, "to": before}
            return
        kind = w.step(cmd)
        self.anim = {"kind": kind, "t": 0.0, "dur": BASE_STEP, "from": before, "to": (w.x, w.y, w.h, w.d),
                     "cmd": cmd}

    def finish(self, result):
        self.running = False
        self.result = result
        self.highlight = None
        if result == "win":
            done = set(self.save.get("completed", []))
            done.add(self.level_index)
            self.save["completed"] = sorted(done)
            self.write_save()

    def robot_visual(self):
        """Current (x, y, h, dir, extra_lift, shake) for drawing."""
        w = self.world
        a = self.anim
        if not a:
            lift = abs(math.sin(self.time * 6)) * 10 if self.result == "win" else 0
            return w.x, w.y, w.h, w.d, lift, 0
        t = min(1.0, a["t"])
        (x0, y0, h0, d0), (x1, y1, h1, d1) = a["from"], a["to"]
        e = ease(t)
        kind = a["kind"]
        if kind == "move":
            return lerp(x0, x1, e), lerp(y0, y1, e), h0, d0, 0, 0
        if kind == "jump":
            arc = math.sin(t * math.pi) * (BH * 1.6 + max(0, h1 - h0) * BH * 0.5)
            return lerp(x0, x1, t), lerp(y0, y1, t), lerp(h0, h1, t), d0, arc, 0
        if kind == "turn":
            return x0, y0, h0, d0 if t < 0.5 else d1, math.sin(t * math.pi) * 4, 0
        if kind == "activate":
            return x0, y0, h0, d0, math.sin(t * math.pi) * 8, 0
        if kind == "blocked":
            return x0, y0, h0, d0, 0, math.sin(t * math.pi * 6) * 4 * (1 - t)
        return x0, y0, h0, d0, 0, 0

    # ---------- drawing ----------
    def make_background(self):
        bg = pygame.Surface((WIN_W, WIN_H))
        for y in range(WIN_H):
            pygame.draw.line(bg, tuple(int(lerp(a, b, y / WIN_H)) for a, b in zip(BG_TOP, BG_BOTTOM)), (0, y), (WIN_W, y))
        pygame.draw.rect(bg, PANEL_BG, (PANEL_X - 12, 0, WIN_W - PANEL_X + 12, WIN_H))
        pygame.draw.line(bg, (70, 76, 120), (PANEL_X - 12, 0), (PANEL_X - 12, WIN_H), 2)
        return bg

    def draw_tile(self, x, y, h):
        sx, sy = self.iso(x, y, h)
        hw, hh = TW / 2, TH / 2
        depth = h * BH
        left = [(sx - hw, sy), (sx, sy + hh), (sx, sy + hh + depth), (sx - hw, sy + depth)]
        right = [(sx + hw, sy), (sx, sy + hh), (sx, sy + hh + depth), (sx + hw, sy + depth)]
        top = [(sx, sy - hh), (sx + hw, sy), (sx, sy + hh), (sx - hw, sy)]
        s = self.screen
        pygame.draw.polygon(s, TILE_LEFT, left)
        pygame.draw.polygon(s, TILE_RIGHT, right)
        for k in range(1, h):
            pygame.draw.line(s, shade(TILE_LEFT, 0.85), (sx - hw, sy + k * BH), (sx, sy + hh + k * BH))
            pygame.draw.line(s, shade(TILE_RIGHT, 0.85), (sx + hw, sy + k * BH), (sx, sy + hh + k * BH))
        pygame.draw.polygon(s, TILE_TOP, top)
        pygame.draw.polygon(s, shade(TILE_TOP, 0.75), top, 2)
        pygame.draw.lines(s, shade(TILE_RIGHT, 0.7), False, [left[0], left[3], left[2], right[3], right[0]], 1)
        if (x, y) in self.level.pads:
            lit = (x, y) in self.world.lit
            inner = [(sx, sy - hh * 0.62), (sx + hw * 0.62, sy), (sx, sy + hh * 0.62), (sx - hw * 0.62, sy)]
            if lit:
                glow = pygame.Surface((TW * 1.5, TH * 1.5), pygame.SRCALPHA)
                pulse = 0.75 + 0.25 * math.sin(self.time * 4)
                for r in range(4):
                    pygame.draw.ellipse(glow, (255, 214, 90, int(26 * pulse)),
                                        glow.get_rect().inflate(-r * TW * 0.22, -r * TH * 0.22))
                s.blit(glow, glow.get_rect(center=(sx, sy)))
                pygame.draw.polygon(s, PAD_ON, inner)
                pygame.draw.polygon(s, PAD_ON_EDGE, inner, 2)
            else:
                pygame.draw.polygon(s, PAD_OFF, inner)
                pygame.draw.polygon(s, PAD_OFF_EDGE, inner, 2)

    def draw_robot(self, vis):
        x, y, h, d, lift, shake = vis
        sx, sy = self.iso(x, y, h)
        sprite = self.sprites[d]
        ax, ay = self.anchor
        self.screen.blit(sprite, (sx - ax + shake, sy - ay - lift))

    def draw_board(self):
        vis = self.robot_visual()
        if self.anim:
            (x0, y0, *_), (x1, y1, *_) = self.anim["from"], self.anim["to"]
            robot_key = max((x0 + y0, x0), (x1 + y1, x1))
        else:
            robot_key = (self.world.x + self.world.y, self.world.x)
        for (x, y) in sorted(self.level.heights, key=lambda p: (p[0] + p[1], p[0])):
            self.draw_tile(x, y, self.level.heights[(x, y)])
            if (x + y, x) == robot_key:
                self.draw_robot(vis)

    def draw_header(self):
        s = self.screen
        title = self.font_big.render(f"Level {self.level_index + 1}: {self.level.name}", True, TEXT)
        s.blit(title, (24, 18))
        y = 54
        for line in self.wrap(self.level.hint, self.font, BOARD.w - 48):
            s.blit(self.font.render(line, True, MUTED), (24, y))
            y += 22
        lit = len(self.world.lit)
        total = len(self.level.pads)
        info = self.font.render(f"Beacons {lit}/{total}", True, PAD_ON if lit == total else TEXT)
        s.blit(info, (BOARD.right - info.get_width() - 24, WIN_H - 52))

    def draw_panel(self, mouse):
        s = self.screen
        s.blit(self.font.render("COMMANDS", True, MUTED), (PANEL_X + 12, 24))
        for cmd, r in self.palette_rects:
            draw_tile_button(s, cmd, r)
        for prog, (box, slots) in self.boxes.items():
            sel = prog == self.selected
            pygame.draw.rect(s, (44, 50, 84), box, border_radius=12)
            pygame.draw.rect(s, ACCENT if sel else (70, 78, 120), box, 3 if sel else 2, border_radius=12)
            label = self.font.render(PROG_LABELS[prog], True, ACCENT if sel else TEXT)
            s.blit(label, (box.x + 14, box.y + 9))
            count = self.font_small.render(f"{len(self.programs[prog])}/{len(slots)}", True, MUTED)
            s.blit(count, (box.right - count.get_width() - 14, box.y + 11))
            dragging = self.drag and self.drag["moved"] and box.collidepoint(mouse)
            for i, r in enumerate(slots):
                prog_cmds = self.programs[prog]
                if i < len(prog_cmds):
                    src = self.drag["src"] if self.drag and self.drag["moved"] else None
                    draw_tile_button(s, prog_cmds[i], r, highlight=self.highlight == (prog, i),
                                     dim=src == (prog, i))
                else:
                    pygame.draw.rect(s, (36, 40, 68), r, border_radius=10)
                    pygame.draw.rect(s, (60, 66, 104), r, 1, border_radius=10)
                if dragging and r.collidepoint(mouse):
                    pygame.draw.line(s, ACCENT, (r.x - GAP / 2, r.y), (r.x - GAP / 2, r.bottom), 3)
        tips = ["Click or drag commands in; click a placed tile to remove it.",
                "Space: run/stop   Tab: switch program   Backspace: undo"]
        for i, tip in enumerate(tips):
            s.blit(self.font_small.render(tip, True, MUTED), (PANEL_X, WIN_H - 118 + i * 20))
        self.buttons[0].label = "Stop" if self.running else ("Reset" if self.result else "Run")
        self.buttons[0].color = (200, 90, 60) if (self.running or self.result) else (46, 160, 90)
        for b in self.buttons:
            b.draw(s, self.font, mouse)

    def overlay_next_rect(self):
        return pygame.Rect(BOARD.centerx - 90, BOARD.y + 120, 180, 50)

    def draw_result(self, mouse):
        s = self.screen
        if self.result == "win":
            msg = self.font_huge.render("All beacons lit!", True, PAD_ON)
            s.blit(msg, msg.get_rect(center=(BOARD.centerx, BOARD.y + 70)))
            last = self.level_index == len(self.levels) - 1
            Button("Play again" if last else "Next level", self.overlay_next_rect(),
                   lambda: None, (46, 160, 90)).draw(s, self.font, mouse)
        elif self.result in ("fail", "overflow"):
            text = "Too many steps - is something looping forever?" if self.result == "overflow" \
                else "Some beacons are still dark. Press Reset and try again."
            msg = self.font.render(text, True, (255, 150, 140))
            box = msg.get_rect(center=(BOARD.centerx, BOARD.y + 40)).inflate(30, 18)
            pygame.draw.rect(s, (60, 30, 40), box, border_radius=10)
            s.blit(msg, msg.get_rect(center=box.center))

    def level_grid_rects(self):
        cols = 4
        w, h = 200, 110
        x0 = (WIN_W - cols * (w + 20)) // 2 + 10
        return [pygame.Rect(x0 + (i % cols) * (w + 20), 180 + (i // cols) * (h + 20), w, h)
                for i in range(len(self.levels))]

    def draw_level_select(self, mouse):
        s = self.screen
        shade_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        shade_surf.fill((10, 12, 24, 220))
        s.blit(shade_surf, (0, 0))
        title = self.font_huge.render("Choose a level", True, TEXT)
        s.blit(title, title.get_rect(center=(WIN_W // 2, 110)))
        done = set(self.save.get("completed", []))
        for i, r in enumerate(self.level_grid_rects()):
            hover = r.collidepoint(mouse)
            col = (60, 120, 80) if i in done else (60, 66, 110)
            pygame.draw.rect(s, shade(col, 1.25 if hover else 1), r, border_radius=14)
            if i == self.level_index:
                pygame.draw.rect(s, ACCENT, r, 3, border_radius=14)
            num = self.font_big.render(str(i + 1), True, TEXT)
            s.blit(num, num.get_rect(center=(r.centerx, r.y + 36)))
            name = self.font_small.render(self.levels[i].name, True, TEXT)
            s.blit(name, name.get_rect(center=(r.centerx, r.y + 72)))
            if i in done:
                s.blit(self.font_small.render("complete", True, PAD_ON), (r.x + 10, r.bottom - 22))
        hint = self.font.render("Click a level, or press Esc to go back", True, MUTED)
        s.blit(hint, hint.get_rect(center=(WIN_W // 2, WIN_H - 60)))

    @staticmethod
    def wrap(text, font, width):
        lines, cur = [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if font.size(trial)[0] > width and cur:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        return lines + ([cur] if cur else [])

    def draw(self):
        mouse = self.to_logical(pygame.mouse.get_pos())
        self.screen.blit(self.background, (0, 0))
        self.draw_board()
        self.draw_header()
        self.draw_panel(mouse)
        for b in self.nav_buttons:
            b.draw(self.screen, self.font, mouse)
        self.draw_result(mouse)
        if self.drag and self.drag["moved"]:
            draw_tile_button(self.screen, self.drag["cmd"], pygame.Rect(0, 0, SLOT, SLOT).move(
                mouse[0] - SLOT // 2, mouse[1] - SLOT // 2))
        if self.show_levels:
            self.draw_level_select(mouse)
        pygame.transform.scale(self.screen, self.window.get_size(), self.window)
        pygame.display.flip()

    @staticmethod
    def to_logical(pos):
        return pos[0] // SCALE, pos[1] // SCALE

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.write_save()
                    pygame.quit()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_mouse_down(self.to_logical(event.pos))
                elif event.type == pygame.MOUSEMOTION:
                    self.on_mouse_move(self.to_logical(event.pos))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.on_mouse_up(self.to_logical(event.pos))
                elif event.type == pygame.KEYDOWN:
                    self.on_key(event.key)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
