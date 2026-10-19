"""Game rules for Bytewise: level loading, robot movement, program interpreter.

Pure logic with no pygame dependency, so it can be unit tested headlessly.
"""
import json
from pathlib import Path

# Direction index -> grid delta. 0:+x (screen SE), 1:+y (SW), 2:-x (NW), 3:-y (NE).
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
DIR_NAMES = ["se", "sw", "nw", "ne"]

FORWARD, LEFT, RIGHT, JUMP, ACTIVATE, P1, P2 = "F", "L", "R", "J", "A", "P1", "P2"
ALL_COMMANDS = [FORWARD, LEFT, RIGHT, JUMP, ACTIVATE, P1, P2]
PROGRAMS = ["main", "p1", "p2"]
CALLS = {P1: "p1", P2: "p2"}

MAX_STEPS = 1000
MAX_DEPTH = 200


class Level:
    def __init__(self, data):
        self.name = data["name"]
        self.hint = data.get("hint", "")
        self.heights = {}
        for y, row in enumerate(data["heights"]):
            for x, ch in enumerate(row):
                if ch != ".":
                    self.heights[(x, y)] = int(ch)
        self.pads = {tuple(p) for p in data["pads"]}
        self.start = tuple(data["start"])
        self.commands = data.get("commands", ALL_COMMANDS)
        self.limits = {name: data.get("limits", {}).get(name, 0) for name in PROGRAMS}


def load_levels(path=Path(__file__).with_name("levels.json")):
    with open(path) as f:
        return [Level(d) for d in json.load(f)]


class World:
    """Mutable robot + beacon state for one run of a level."""

    def __init__(self, level):
        self.level = level
        self.x, self.y, self.d = level.start
        self.lit = set()

    @property
    def h(self):
        return self.level.heights[(self.x, self.y)]

    def ahead(self):
        dx, dy = DIRS[self.d]
        return self.x + dx, self.y + dy

    def won(self):
        return self.lit == self.level.pads

    def step(self, cmd):
        """Apply one primitive command. Returns an event name for the animator."""
        if cmd == LEFT:
            self.d = (self.d - 1) % 4
            return "turn"
        if cmd == RIGHT:
            self.d = (self.d + 1) % 4
            return "turn"
        if cmd == ACTIVATE:
            pos = (self.x, self.y)
            if pos not in self.level.pads:
                return "blocked"
            self.lit ^= {pos}
            return "activate"
        if cmd in (FORWARD, JUMP):
            target = self.ahead()
            th = self.level.heights.get(target)
            if th is None:
                return "blocked"
            if cmd == FORWARD and th == self.h:
                self.x, self.y = target
                return "move"
            if cmd == JUMP and (th == self.h + 1 or th < self.h):
                self.x, self.y = target
                return "jump"
            return "blocked"
        raise ValueError(f"unknown command {cmd!r}")


class Interpreter:
    """Steps through main/p1/p2 one instruction at a time, following calls."""

    def __init__(self, programs):
        self.programs = programs
        self.stack = [["main", 0]]
        self.steps = 0
        self.overflow = False

    def next(self):
        """Return (program, index, command) for the next instruction, or None when done."""
        while self.stack:
            frame = self.stack[-1]
            prog, idx = frame
            if idx >= len(self.programs[prog]):
                self.stack.pop()
                continue
            frame[1] += 1
            self.steps += 1
            if self.steps > MAX_STEPS:
                self.overflow = True
                return None
            cmd = self.programs[prog][idx]
            if cmd in CALLS:
                if len(self.stack) >= MAX_DEPTH:
                    self.overflow = True
                    return None
                self.stack.append([CALLS[cmd], 0])
            return prog, idx, cmd
        return None


def run(level, programs):
    """Run a program to completion headlessly. Returns the final World."""
    world = World(level)
    interp = Interpreter(programs)
    while not world.won():
        nxt = interp.next()
        if nxt is None:
            break
        cmd = nxt[2]
        if cmd not in CALLS:
            world.step(cmd)
    return world
