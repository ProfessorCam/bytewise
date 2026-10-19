"""Generates the default orange robot sprites in assets/robot/.

One PNG per facing direction: robot_se.png, robot_sw.png, robot_nw.png, robot_ne.png.
Replace any of them with your own art to reskin the robot (see README.md).
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).with_name("assets") / "robot"
W, H = 56, 76          # final sprite size in pixels
ANCHOR = (28, 66)      # pixel that sits on the tile centre (robot's footprint centre)
S = 4                  # supersampling factor for smooth edges

ORANGE_TOP = (255, 176, 78)
ORANGE_LEFT = (240, 125, 32)
ORANGE_RIGHT = (205, 96, 18)
OUTLINE = (92, 42, 10)
DARK = (34, 32, 44)
EYE = (110, 235, 255)
STEEL = (150, 158, 172)
STEEL_DARK = (96, 102, 116)
BULB = (255, 226, 90)


def sc(points):
    return [(x * S, y * S) for x, y in points]


class Cube:
    """Isometric box. (cx, by) is the bottom-front vertex; w is half-width; h is height."""

    def __init__(self, cx, by, w, h):
        self.cx, self.by, self.w, self.h = cx, by, w, h

    def left(self, u, v):
        return (self.cx - self.w + u * self.w, self.by - self.w / 2 + u * self.w / 2 - v * self.h)

    def right(self, u, v):
        return (self.cx + u * self.w, self.by - u * self.w / 2 - v * self.h)

    def top_center(self):
        return (self.cx, self.by - self.h - self.w / 2)

    def face(self, side, u0, v0, u1, v1):
        f = self.left if side == "left" else self.right
        return [f(u0, v0), f(u1, v0), f(u1, v1), f(u0, v1)]

    def draw(self, d, top, left, right):
        cx, by, w, h = self.cx, self.by, self.w, self.h
        lw = int(S * 0.9)
        d.polygon(sc(self.face("left", 0, 0, 1, 1)), fill=left, outline=OUTLINE, width=lw)
        d.polygon(sc(self.face("right", 0, 0, 1, 1)), fill=right, outline=OUTLINE, width=lw)
        d.polygon(sc([(cx, by - h), (cx + w, by - w / 2 - h), (cx, by - w - h), (cx - w, by - w / 2 - h)]),
                  fill=top, outline=OUTLINE, width=lw)


def quad(d, cube, side, u0, v0, u1, v1, fill):
    d.polygon(sc(cube.face(side, u0, v0, u1, v1)), fill=fill)


def make_robot(front_side, show_face):
    """front_side: which visible face ('left'/'right') holds the face or the backpack.
    show_face: True when the robot faces the viewer, False when we see its back."""
    side_side = "right" if front_side == "left" else "left"
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # soft shadow under the robot
    ax, ay = ANCHOR
    d.ellipse(sc([(ax - 20, ay - 6), (ax + 20, ay + 6)]), fill=(0, 0, 0, 70))

    body = Cube(ax, ay + 9, 18, 20)
    body.draw(d, ORANGE_TOP, ORANGE_LEFT, ORANGE_RIGHT)
    # tread band
    for side in ("left", "right"):
        quad(d, body, side, 0.04, 0.04, 0.96, 0.22, DARK)
        for u in (0.2, 0.45, 0.7):
            quad(d, body, side, u, 0.08, u + 0.1, 0.18, STEEL_DARK)
    if show_face:
        quad(d, body, front_side, 0.22, 0.36, 0.78, 0.82, (255, 210, 150))
        quad(d, body, front_side, 0.30, 0.46, 0.50, 0.70, BULB)
        quad(d, body, front_side, 0.56, 0.46, 0.70, 0.56, STEEL_DARK)
        quad(d, body, front_side, 0.56, 0.60, 0.70, 0.70, STEEL_DARK)
    else:
        quad(d, body, front_side, 0.18, 0.32, 0.82, 0.90, (180, 80, 14))
        for v in (0.45, 0.58, 0.71):
            quad(d, body, front_side, 0.28, v, 0.72, v + 0.05, DARK)
    # shoulder / arm on the side
    quad(d, body, side_side, 0.36, 0.30, 0.64, 0.92, STEEL)
    quad(d, body, side_side, 0.40, 0.36, 0.60, 0.86, STEEL_DARK)

    hx, hy = body.top_center()
    head = Cube(hx, hy + 7 - 1, 14, 16)
    head.draw(d, ORANGE_TOP, ORANGE_LEFT, ORANGE_RIGHT)
    if show_face:
        quad(d, head, front_side, 0.10, 0.28, 0.90, 0.82, DARK)
        quad(d, head, front_side, 0.20, 0.44, 0.42, 0.70, EYE)
        quad(d, head, front_side, 0.58, 0.44, 0.80, 0.70, EYE)
        quad(d, head, front_side, 0.24, 0.58, 0.32, 0.68, (230, 255, 255))
        quad(d, head, front_side, 0.62, 0.58, 0.70, 0.68, (230, 255, 255))
    else:
        quad(d, head, front_side, 0.25, 0.35, 0.75, 0.75, (180, 80, 14))
    # ear bolt
    ex, ey = head.face(side_side, 0.5, 0.55, 0.5, 0.55)[0]
    d.ellipse(sc([(ex - 3, ey - 3), (ex + 3, ey + 3)]), fill=STEEL, outline=OUTLINE, width=S)

    # antenna
    tx, ty = head.top_center()
    d.line(sc([(tx, ty), (tx, ty - 14)]), fill=OUTLINE, width=int(S * 1.6))
    d.ellipse(sc([(tx - 4, ty - 22), (tx + 4, ty - 14)]), fill=BULB, outline=OUTLINE, width=S)
    d.ellipse(sc([(tx - 2, ty - 20), (tx, ty - 18)]), fill=(255, 255, 230))

    return img.resize((W, H), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # direction -> (face that points "forward", is the front visible?)
    variants = {"se": ("right", True), "sw": ("left", True),
                "nw": ("right", False), "ne": ("left", False)}
    for name, (side, front) in variants.items():
        path = OUT / f"robot_{name}.png"
        make_robot(side, front).save(path)
        print("wrote", path)
    (OUT / "sprite.json").write_text(json.dumps({"anchor": list(ANCHOR), "scale": 1.0}, indent=1) + "\n")


if __name__ == "__main__":
    main()
