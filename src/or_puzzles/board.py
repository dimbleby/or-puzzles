#!/usr/bin/env python3


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
    def __init__(
        self, cell_coverers: dict[tuple[int, int], list[tuple[int, cp_model.IntVar]]]
    ) -> None:
        super().__init__()
        self.cell_coverers = cell_coverers
        self.solution_count = 0

    def on_solution_callback(self) -> None:
        self.solution_count += 1
        for y in reversed(range(8)):
            row = [self._piece_at(x, y) for x in range(8)]
            pretty_row = [f"{index:02d}" for index in row]
            print(" ".join(pretty_row))
        print()

    def _piece_at(self, x: int, y: int) -> int:
        return next(i for i, c in self.cell_coverers[x, y] if self.value(c))


def main() -> None:
    model = cp_model.CpModel()

    # What are the possible placements for each piece?
    possibilities = {index: piece.placements() for index, piece in enumerate(PIECES)}

    # choices[i, j] is true iff we pick possibility j for piece i.
    choices = {
        (i, j): model.new_bool_var(f"piece_{i}_{j}")
        for i, placements in possibilities.items()
        for j in range(len(placements))
    }

    # We must choose exactly one placement for each piece.
    for i, placements in possibilities.items():
        piece_choices = [choices[i, j] for j in range(len(placements))]
        model.add_exactly_one(piece_choices)

    # For each cell, which (piece_index, choice_var) pairs can cover it?
    cell_coverers: dict[tuple[int, int], list[tuple[int, cp_model.IntVar]]] = {
        (x, y): [] for x in range(8) for y in range(8)
    }
    for (i, j), choice in choices.items():
        for cell in possibilities[i][j].cells:
            cell_coverers[cell.x, cell.y].append((i, choice))

    # We must cover each cell exactly once.
    for coverers in cell_coverers.values():
        model.add_exactly_one(c for _, c in coverers)

    # Break rotational symmetry: piece covering (0,0) must be less than (7,7).
    for i_a, choice_a in cell_coverers[0, 0]:
        for i_b, choice_b in cell_coverers[7, 7]:
            if i_b <= i_a:
                model.add_bool_or([choice_a.negated(), choice_b.negated()])

    # Decision strategy: branch on pieces with fewest placements first.
    ordered_vars = []
    for i in sorted(possibilities, key=lambda i: len(possibilities[i])):
        ordered_vars.extend(choices[i, j] for j in range(len(possibilities[i])))
    model.add_decision_strategy(
        ordered_vars, cp_model.CHOOSE_FIRST, cp_model.SELECT_MAX_VALUE
    )

    # Solve.
    solution_printer = SolutionPrinter(cell_coverers)
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.search_branching = cp_model.FIXED_SEARCH
    solver.solve(model, solution_printer)
    print(f"Found {solution_printer.solution_count} solutions")


if __name__ == "__main__":
    main()
