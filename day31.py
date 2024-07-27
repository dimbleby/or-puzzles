#!/usr/bin/env python3

from __future__ import annotations

import itertools
from pathlib import Path
from typing import ClassVar

from attrs import frozen
from ortools.sat.python import cp_model


@frozen
class Tile:
    LETTERS: ClassVar[str] = "BCFLMRT"
    symbols: list[int]

    @staticmethod
    def from_string(text: str) -> Tile:
        symbols = [Tile.LETTERS.index(char) for char in text]
        return Tile(symbols)

    def rotate(self, turns: int) -> Tile:
        assert 0 <= turns < 4
        symbols = self.symbols[turns:] + self.symbols[:turns]
        return Tile(symbols)


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(
        self,
        choices: dict[tuple[int, int, int, int], cp_model.IntVar],
        corners: dict[tuple[int, int, int], cp_model.IntVar],
    ) -> None:
        super().__init__()
        self.choices = choices
        self.corners = corners

    def on_solution_callback(self) -> None:
        for y in reversed(range(7)):
            if y != 6:
                tiles = [self.get_tile(x, y) for x in range(6)]
                pretty_row = [f"{tile + 1:02d}" for tile in tiles]
                print(f" {' '.join(pretty_row)}")

            corners = [self.get_corner(x, y) for x in range(7)]
            pretty_row = [f"{Tile.LETTERS[corner]}" for corner in corners]
            print("  ".join(pretty_row))

    def get_corner(self, x: int, y: int) -> int:
        return sum(s * self.Value(self.corners[x, y, s]) for s in range(7))

    def get_tile(self, x: int, y: int) -> int:
        return sum(
            i * self.Value(self.choices[i, x, y, r])
            for i in range(36)
            for r in range(4)
        )


def solve() -> None:
    with Path("day31.txt").open(encoding="utf-8") as f:
        data = f.read()

    tiles = [Tile.from_string(line) for line in data.splitlines()]

    model = cp_model.CpModel()

    # choices[i, x, y, r] is true iff we put tile i in cell (x,y) with rotation r.
    choices = {
        (i, x, y, r): model.NewBoolVar(f"tile_{i}_{x}_{y}_{r}")
        for i in range(len(tiles))
        for x in range(6)
        for y in range(6)
        for r in range(4)
    }

    # corners[x, y, s] is true iff the corner at (x,y) contains symbol s.
    corners = {
        (x, y, s): model.NewBoolVar(f"corner_{x}_{y}_{s}")
        for x in range(7)
        for y in range(7)
        for s in range(7)
    }

    # Placing a tile puts a symbol in each corner.
    for (i, x, y, r), choice in choices.items():
        tile = tiles[i].rotate(r)
        model.AddImplication(choice, corners[x, y, tile.symbols[0]])
        model.AddImplication(choice, corners[x, y + 1, tile.symbols[1]])
        model.AddImplication(choice, corners[x + 1, y + 1, tile.symbols[2]])
        model.AddImplication(choice, corners[x + 1, y, tile.symbols[3]])

    # We must make exactly one choice for each tile.
    for i in range(len(tiles)):
        model.AddExactlyOne(
            choices[i, x, y, r] for x in range(6) for y in range(6) for r in range(4)
        )

    # We must make exactly one choice for each square.
    for x, y in itertools.product(range(6), range(6)):
        model.AddExactlyOne(
            choices[i, x, y, r] for i in range(len(tiles)) for r in range(4)
        )

    # Each corner contains exactly one symbol.
    for x, y in itertools.product(range(7), range(7)):
        model.AddExactlyOne(corners[x, y, s] for s in range(7))

    # Solve.
    solution_printer = SolutionPrinter(choices, corners)
    solver = cp_model.CpSolver()
    solver.Solve(model, solution_printer)


if __name__ == "__main__":
    solve()
