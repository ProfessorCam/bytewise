"""Checks that every level is solvable within its slot limits.

Run with: python -m pytest test_levels.py   (or just: python test_levels.py)
"""
from engine import ALL_COMMANDS, PROGRAMS, load_levels, run

# Reference solutions, one per level, in level order.
SOLUTIONS = [
    {"main": "F F F A"},
    {"main": "F F R F F A"},
    {"main": "F F F A R F F R F F F A"},
    {"main": "F J J A"},
    {"main": "J J A J J A"},
    {"main": "J J A R J J A"},
    {"main": "P1 P1 P1 P1", "p1": "F F F F A R"},
    {"main": "P1 P1 P1", "p1": "J R J A L"},
    {"main": "P1 P1 P1", "p1": "F R P2 R F", "p2": "F F A R R F F"},
    {"main": "P1", "p1": "F F A P1"},
    {"main": "P1 P1 P1 P1 P2", "p1": "J J J J A R", "p2": "J R J L J R J A"},
    {"main": "P1", "p1": "J R J A L P1"},
]


def parse(solution):
    return {name: solution.get(name, "").split() for name in PROGRAMS}


def test_every_level_has_a_solution():
    assert len(load_levels()) == len(SOLUTIONS)


def test_solutions_win_within_limits():
    for i, (level, sol) in enumerate(zip(load_levels(), SOLUTIONS), 1):
        programs = parse(sol)
        for name, prog in programs.items():
            assert len(prog) <= level.limits[name], f"level {i}: {name} too long"
            assert all(c in level.commands for c in prog), f"level {i}: disallowed command"
        assert run(level, programs).won(), f"level {i} ({level.name}) not solved"


def test_levels_are_well_formed():
    for level in load_levels():
        assert level.start[:2] in level.heights
        assert level.pads <= set(level.heights)
        assert set(level.commands) <= set(ALL_COMMANDS)


def test_empty_program_does_not_win():
    for level in load_levels():
        assert not run(level, parse({})).won()


def test_infinite_recursion_terminates():
    level = load_levels()[0]
    world = run(level, parse({"main": "P1", "p1": "L P1"}))
    assert not world.won()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
