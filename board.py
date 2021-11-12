#!/bin/env python
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Coord:
    x: int
    y: int

    def __add__(self, other: "Coord") -> "Coord":
        return Coord(self.x + other.x, self.y + other.y)


@dataclass
class Piece:
    # White indicates whether the cell in the bottom-left corner of the rectangle
    # bounding the piece must be white.
    cells: Set[Coord]
    white: bool

    def rotate(self, turns: int) -> "Piece":
        max_x = max(cell.x for cell in self.cells)
        max_y = max(cell.y for cell in self.cells)

        if turns == 0:
            cells = self.cells
            white = self.white

        elif turns == 1:
            cells = {Coord(cell.y, max_x - cell.x) for cell in self.cells}
            white = self.white ^ (max_x % 2 == 1)

        elif turns == 2:
            cells = {Coord(max_x - cell.x, max_y - cell.y) for cell in self.cells}
            white = self.white ^ ((max_x + max_y) % 2 == 1)

        elif turns == 3:
            cells = {Coord(max_y - cell.y, cell.x) for cell in self.cells}
            white = self.white ^ (max_y % 2 == 1)

        return Piece(cells, white)

    def rotations(self) -> List["Piece"]:
        pieces = [self.rotate(turns) for turns in [0, 1, 2, 3]]
        unique = []
        for piece in pieces:
            if piece not in unique:
                unique.append(piece)
        return unique

    def add(self, shift: Coord) -> "Piece":
        cells = {cell + shift for cell in self.cells}
        return Piece(cells, self.white)

    def shifts(self) -> List["Piece"]:
        max_x = max(cell.x for cell in self.cells)
        max_y = max(cell.y for cell in self.cells)

        # Here is where we enforce matching colours.
        bottom_lefts = [
            Coord(x, y)
            for x in range(8 - max_x)
            for y in range(8 - max_y)
            if self.white ^ ((x + y) % 2 == 0)
        ]
        pieces = [self.add(bottom_left) for bottom_left in bottom_lefts]

        return pieces

    def placements(self) -> List["Piece"]:
        pieces = [piece for rotation in self.rotations() for piece in rotation.shifts()]
        return pieces


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


class SolutionPrinter(cp_model.CpSolverSolutionCallback):  # type: ignore
    def __init__(self, covers: Dict[Tuple[int, int], cp_model.IntVar]):
        cp_model.CpSolverSolutionCallback.__init__(self)
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

    # We must choose exactly one placement for each piece
    for index, placements in possibilities.items():
        model.Add(sum(choices[index, j] for j in range(len(placements))) == 1)

    # What piece is covering cell x, y?
    covers = {
        (x, y): model.NewIntVar(0, len(PIECES) - 1, f"cell_{x}_{y}")
        for x in range(8)
        for y in range(8)
    }

    # Placing a piece covers cells - and prevents other cells from using that piece.
    for (i, j), choice in choices.items():
        placement = possibilities[i][j]
        for x in range(8):
            for y in range(8):
                constraint = (
                    covers[x, y] == i
                    if Coord(x, y) in placement.cells
                    else covers[x, y] != i
                )
                model.Add(constraint).OnlyEnforceIf(choice)

    # Break rotational symmetry.
    model.Add(covers[7, 0] < covers[0, 7])

    # We'll fill the board from bottom left to top right.
    tagged_covers = [(x + y, cover) for (x, y), cover in covers.items()]
    tagged_covers.sort(key=lambda x: x[0])
    sorted_covers = [cover for _tag, cover in tagged_covers]
    model.AddDecisionStrategy(
        sorted_covers, cp_model.CHOOSE_FIRST, cp_model.SELECT_MIN_VALUE
    )

    # Solve.
    solution_printer = SolutionPrinter(covers)
    solver = cp_model.CpSolver()
    solver.parameters.search_branching = cp_model.FIXED_SEARCH
    solver.parameters.enumerate_all_solutions = True
    solver.Solve(model, solution_printer)
    print(f"Found {solution_printer.solution_count} solutions")


if __name__ == "__main__":
    main()
