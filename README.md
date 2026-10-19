# Bytewise

An isometric programming-puzzle game in Python/pygame. Program the orange robot with
command tiles so it powers up every beacon on the board.

## Requirements

- Python 3.9 or newer
- [pygame](https://www.pygame.org/) 2.5+ (runs the game)
- [Pillow](https://python-pillow.org/) 10+ (only needed to regenerate the robot sprites)

## Install

From the project folder, create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

(Using conda instead? Run `conda install -c conda-forge pygame pillow` in your environment.)

## Run

```bash
python main.py
```

The window opens at 2400×1520. If that's too big for your screen, set `SCALE = 1` near
the top of `main.py` for a 1200×760 window.

To check that every level can still be solved after you edit `levels.json`:

```bash
python test_levels.py            # or: python -m pytest test_levels.py
```

To regenerate the default robot sprites in `assets/robot/`:

```bash
python make_sprites.py
```

### Troubleshooting

- **`ModuleNotFoundError: No module named 'pygame'`**: the virtual environment isn't
  active. Run `source .venv/bin/activate` again, or use `.venv/bin/python main.py`.
- **No window appears on Linux**: you need a graphical session (X11 or Wayland).
  Over SSH, the game can't open a window unless you have display forwarding.
- **Missing robot images**: if `assets/robot/*.png` are deleted, the game redraws them
  on startup. This needs Pillow installed.
- **To reset progress**, delete `save.json`.

## How to play

| Tile | Command   | What it does |
|------|-----------|--------------|
| ↑    | Forward   | Step one tile ahead (only onto a tile of the same height) |
| ↰ ↱  | Turn L/R  | Rotate 90° in place |
| ⤴    | Jump      | Hop forward up exactly one block, or down any number of blocks |
| 💡   | Activate  | Toggle the beacon under the robot |
| P1/P2| Procedure | Run the P1/P2 program, then continue (procedures may call themselves) |

- Click a command to add it to the selected program (orange outline), or drag it to a slot.
- Click a placed tile to remove it, or drag it to move it between programs.
- **Space** run/stop · **Tab** switch program · **Backspace** remove last · arrows / `J` / `A` / `1` / `2` add commands.

Progress and your programs are saved to `save.json`.

## Swapping the robot

The robot is four PNGs in `assets/robot/`, one per facing direction:

| File           | Facing (on screen) |
|----------------|--------------------|
| `robot_se.png` | down-right (toward viewer) |
| `robot_sw.png` | down-left (toward viewer)  |
| `robot_nw.png` | up-left (away from viewer) |
| `robot_ne.png` | up-right (away from viewer)|

Drop in your own transparent PNGs with the same names (any size). `assets/robot/sprite.json` controls placement:

```json
{"anchor": [28, 66], "scale": 1.0}
```

`anchor` is the pixel in your image that should sit on the centre of the tile (the robot's
feet), and `scale` resizes the images. If `sprite.json` is missing, the anchor defaults to
the horizontal centre, 87% of the way down. Run `python make_sprites.py` to regenerate
the default orange robot.

## Levels

The levels live in `levels.json`. Each `heights` row is a string of digits, one per tile
(`.` means no tile). `start` is `[x, y, dir]`, where dir is 0=SE, 1=SW, 2=NW, 3=NE.
`limits` sets the slot count for `main`/`p1`/`p2` (0 or missing hides that program).
`python test_levels.py` checks that every level can be solved. Add a reference solution
to `SOLUTIONS` there whenever you add a level.

## Files

- `main.py`: pygame rendering, input, and animation
- `engine.py`: game rules and program interpreter (no pygame)
- `make_sprites.py`: draws the default robot PNGs with Pillow
- `levels.json`: level data
- `test_levels.py`: solvability tests
