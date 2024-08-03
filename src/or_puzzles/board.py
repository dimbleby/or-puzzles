#!/usr/bin/env python3
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterable


@dataclass(frozen=True)
class Cell:
    x: int
    y: int

    def __add__(self, other: Cell) -> Cell:
        return Cell(self.x + other.x, self.y + other.y)


class Piece:
    def __init__(self, cells: Iterable[Cell], *, white: bool) -> None:
        # White indicates whether the cell in the bottom-left corner of the rectangle
        # bounding the piece must be white.
        self.cells = frozenset(cells)
        self.white = white

    def __key(self) -> tuple[Hashable, ...]:
        return (self.cells, self.white)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Piece):
            return NotImplemented

        return self.__key() == other.__key()

    @override
    def __hash__(self) -> int:
        return hash(self.__key())

    def rotate(self, turns: int) -> Piece:
        max_x = max(cell.x for cell in self.cells)
        max_y = max(cell.y for cell in self.cells)
        cells: Iterable[Cell]

        if turns == 0:
            cells = self.cells
            white = self.white

        elif turns == 1:
            cells = (Cell(cell.y, max_x - cell.x) for cell in self.cells)
            white = self.white ^ (max_x % 2 == 1)

        elif turns == 2:
            cells = (Cell(max_x - cell.x, max_y - cell.y) for cell in self.cells)
            white = self.white ^ ((max_x + max_y) % 2 == 1)

        else:
            assert turns == 3
            cells = (Cell(max_y - cell.y, cell.x) for cell in self.cells)
            white = self.white ^ (max_y % 2 == 1)

        return Piece(cells, white=white)

    def rotations(self) -> set[Piece]:
        return {self.rotate(turns) for turns in range(4)}

    def add(self, shift: Cell) -> Piece:
        cells = (cell + shift for cell in self.cells)
        return Piece(cells, white=self.white)

    def shifts(self) -> list[Piece]:
        max_x = max(cell.x for cell in self.cells)
        max_y = max(cell.y for cell in self.cells)

        # Here is where we enforce matching colours.
        bottom_lefts = (
            Cell(x, y)
            for x in range(8 - max_x)
            for y in range(8 - max_y)
            if self.white ^ ((x + y) % 2 == 0)
        )
        return [self.add(bottom_left) for bottom_left in bottom_lefts]

    def placements(self) -> list[Piece]:
        return [piece for rotation in self.rotations() for piece in rotation.shifts()]


PIECES = [
    Piece({Cell(0, 0), Cell(0, 1), Cell(1, 1), Cell(2, 1)}, white=False),
    Piece({Cell(0, 0), Cell(1, 0), Cell(1, 1), Cell(2, 1)}, white=False),
    Piece({Cell(0, 1), Cell(1, 1), Cell(2, 0), Cell(2, 1), Cell(3, 1)}, white=True),
    Piece({Cell(0, 1), Cell(1, 1), Cell(2, 0), Cell(2, 1)}, white=True),
    Piece({Cell(0, 1), Cell(1, 0), Cell(1, 1), Cell(2, 0), Cell(3, 0)}, white=False),
    Piece({Cell(0, 1), Cell(1, 1), Cell(2, 1), Cell(3, 0), Cell(3, 1)}, white=False),
    Piece({Cell(0, 0), Cell(1, 0), Cell(2, 0), Cell(2, 1), Cell(3, 0)}, white=True),
    Piece({Cell(0, 1), Cell(0, 2), Cell(1, 1), Cell(2, 0), Cell(2, 1)}, white=True),
    Piece({Cell(0, 0), Cell(1, 0), Cell(2, 0), Cell(3, 0), Cell(3, 1)}, white=False),
    Piece({Cell(0, 0), Cell(0, 1), Cell(1, 1), Cell(2, 1), Cell(2, 2)}, white=False),
    Piece({Cell(0, 0), Cell(1, 0), Cell(1, 1), Cell(2, 1), Cell(3, 1)}, white=False),
    Piece({Cell(0, 0), Cell(0, 1), Cell(1, 1), Cell(1, 2), Cell(2, 2)}, white=True),
    Piece({Cell(0, 0), Cell(1, 0), Cell(1, 1)}, white=True),
    Piece({Cell(0, 0), Cell(1, 0), Cell(1, 1), Cell(2, 0)}, white=False),
]


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, covers: dict[tuple[int, int], cp_model.IntVar]) -> None:
        super().__init__()
        self.covers = covers
        self.solution_count = 0

    def on_solution_callback(self) -> None:
        self.solution_count += 1
        for y in reversed(range(8)):
            row = [self.Value(self.covers[x, y]) for x in range(8)]
            pretty_row = [f"{index:02d}" for index in row]
            print(" ".join(pretty_row))
        print()


def main() -> None:
    model = cp_model.CpModel()

    # What are the possible placements for each piece?
    possibilities = {index: piece.placements() for index, piece in enumerate(PIECES)}

    # choices[i, j] is true iff we pick possibility j for piece i.
    choices = {
        (i, j): model.NewBoolVar(f"piece_{i}_{j}")
        for i, placements in possibilities.items()
        for j in range(len(placements))
    }

    # What piece is covering cell x, y?
    covers = {
        (x, y): model.NewIntVar(0, len(PIECES) - 1, f"cell_{x}_{y}")
        for x in range(8)
        for y in range(8)
    }

    # Placing a piece covers cells.
    for (i, j), choice in choices.items():
        for cell in possibilities[i][j].cells:
            model.Add(covers[cell.x, cell.y] == i).OnlyEnforceIf(choice)

    # We must choose exactly one placement for each piece
    for i, placements in possibilities.items():
        piece_choices = [choices[i, j] for j in range(len(placements))]
        model.AddExactlyOne(piece_choices)

    # We must cover each cell exactly once.
    for x, y in itertools.product(range(8), range(8)):
        cell_choices = [
            choice
            for (i, j), choice in choices.items()
            if Cell(x, y) in possibilities[i][j].cells
        ]
        model.AddExactlyOne(cell_choices)

    # Break rotational symmetry.
    model.Add(covers[0, 0] < covers[7, 7])

    # Solve.
    solution_printer = SolutionPrinter(covers)
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.Solve(model, solution_printer)
    print(f"Found {solution_printer.solution_count} solutions")


if __name__ == "__main__":
    main()
