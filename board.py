#!/usr/bin/env python3
from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import frozen
from ortools.sat.python import cp_model
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterable


@frozen
class Coord:
    x: int
    y: int

    def __add__(self, other: Coord) -> Coord:
        return Coord(self.x + other.x, self.y + other.y)


class Piece:
    def __init__(self, cells: Iterable[Coord], white: bool) -> None:
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
        cells: Iterable[Coord]

        if turns == 0:
            cells = self.cells
            white = self.white

        elif turns == 1:
            cells = (Coord(cell.y, max_x - cell.x) for cell in self.cells)
            white = self.white ^ (max_x % 2 == 1)

        elif turns == 2:
            cells = (Coord(max_x - cell.x, max_y - cell.y) for cell in self.cells)
            white = self.white ^ ((max_x + max_y) % 2 == 1)

        elif turns == 3:
            cells = (Coord(max_y - cell.y, cell.x) for cell in self.cells)
            white = self.white ^ (max_y % 2 == 1)

        return Piece(cells, white)

    def rotations(self) -> set[Piece]:
        return {self.rotate(turns) for turns in range(4)}

    def add(self, shift: Coord) -> Piece:
        cells = (cell + shift for cell in self.cells)
        return Piece(cells, self.white)

    def shifts(self) -> list[Piece]:
        max_x = max(cell.x for cell in self.cells)
        max_y = max(cell.y for cell in self.cells)

        # Here is where we enforce matching colours.
        bottom_lefts = (
            Coord(x, y)
            for x in range(8 - max_x)
            for y in range(8 - max_y)
            if self.white ^ ((x + y) % 2 == 0)
        )
        return [self.add(bottom_left) for bottom_left in bottom_lefts]


    def placements(self) -> list[Piece]:
        return [piece for rotation in self.rotations() for piece in rotation.shifts()]


PIECES = [
    Piece({Coord(0, 0), Coord(0, 1), Coord(1, 1), Coord(2, 1)}, False),
    Piece({Coord(0, 0), Coord(1, 0), Coord(1, 1), Coord(2, 1)}, False),
    Piece({Coord(0, 1), Coord(1, 1), Coord(2, 0), Coord(2, 1), Coord(3, 1)}, True),
    Piece({Coord(0, 1), Coord(1, 1), Coord(2, 0), Coord(2, 1)}, True),
    Piece({Coord(0, 1), Coord(1, 0), Coord(1, 1), Coord(2, 0), Coord(3, 0)}, False),
    Piece({Coord(0, 1), Coord(1, 1), Coord(2, 1), Coord(3, 0), Coord(3, 1)}, False),
    Piece({Coord(0, 0), Coord(1, 0), Coord(2, 0), Coord(2, 1), Coord(3, 0)}, True),
    Piece({Coord(0, 1), Coord(0, 2), Coord(1, 1), Coord(2, 0), Coord(2, 1)}, True),
    Piece({Coord(0, 0), Coord(1, 0), Coord(2, 0), Coord(3, 0), Coord(3, 1)}, False),
    Piece({Coord(0, 0), Coord(0, 1), Coord(1, 1), Coord(2, 1), Coord(2, 2)}, False),
    Piece({Coord(0, 0), Coord(1, 0), Coord(1, 1), Coord(2, 1), Coord(3, 1)}, False),
    Piece({Coord(0, 0), Coord(0, 1), Coord(1, 1), Coord(1, 2), Coord(2, 2)}, True),
    Piece({Coord(0, 0), Coord(1, 0), Coord(1, 1)}, True),
    Piece({Coord(0, 0), Coord(1, 0), Coord(1, 1), Coord(2, 0)}, False),
]


class SolutionPrinter(cp_model.CpSolverSolutionCallback):  # type: ignore[misc]
    def __init__(self, covers: dict[tuple[int, int], cp_model.IntVar]):
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
    for x in range(8):
        for y in range(8):
            cell_choices = [
                choice
                for (i, j), choice in choices.items()
                if Coord(x, y) in possibilities[i][j].cells
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
