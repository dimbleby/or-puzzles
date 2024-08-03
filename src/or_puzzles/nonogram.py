#!/usr/bin/env python3
from __future__ import annotations

from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from collections.abc import Iterable


def constrain_line(
    model: cp_model.CpModel,
    line: list[cp_model.IntVar],
    clues: Iterable[int],
    *,
    invert: bool = False,
) -> None:
    """Constrain a line so that it satisfies the description of it in the clues"""
    # We're going to advance through a state machine.  Create some labels to help track
    # this.  Eg clues [2, 3, 2] -> labels [0, 1, 1, 0, 1, 1, 1, 0, 1, 1].
    blank, square = (1, 0) if invert else (0, 1)
    labels = []
    for clue in clues:
        labels.append(blank)
        labels.extend([square] * clue)

    # Wrinkle: when we have no clues, we have a single state.
    if not labels:
        labels = [blank]

    # We must go all the way from the start to the end.
    initial_state = 0
    final_state = len(labels) - 1

    # Construct the valid transitions: given state and input, what's the next state?
    #
    # - in the final state, a blank is acceptable and leaves us still in the final state
    #
    # - else if we're on a blank then another blank leaves us where we are, while
    #   filling a square moves us along
    #
    # - else (we're on a filled square) we're only allowed to move along if we get the
    #   appropriate input.
    transitions = []
    for state, label in enumerate(labels):
        if state == final_state:
            transitions.append((state, blank, state))
        elif label == blank:
            transitions.append((state, blank, state))
            transitions.append((state, square, state + 1))
        else:
            next_label = labels[state + 1]
            transitions.append((state, next_label, state + 1))

    # Add the constraint to the model.
    model.AddAutomaton(line, initial_state, [final_state], transitions)


def solve_puzzle(
    row_clues: Iterable[Iterable[int]],
    column_clues: Iterable[Iterable[int]],
    givens: Iterable[tuple[int, int]] = (),
    *,
    invert_columns: bool = False,
) -> None:
    """Solve a puzzle"""
    # Discard pointless clues.
    row_clues = [[clue for clue in clues if clue > 0] for clues in row_clues]
    column_clues = [[clue for clue in clues if clue > 0] for clues in column_clues]

    # Count rows and columns.
    num_rows = len(row_clues)
    num_columns = len(column_clues)

    # Sanity check.
    row_fills = (sum(clues) for clues in row_clues)
    column_fills = (sum(clues) for clues in column_clues)
    if invert_columns:
        column_fills = (num_rows - filled for filled in column_fills)

    row_wise = sum(row_fills)
    column_wise = sum(column_fills)
    if row_wise != column_wise:
        print(f"{row_wise} row fills != {column_wise} column fills")
        return

    # Prepare a model.
    model = cp_model.CpModel()

    # squares[i, j]: is square i,j filled in?
    squares = {
        (i, j): model.NewBoolVar(f"squares_{i}_{j}")
        for i in range(num_rows)
        for j in range(num_columns)
    }

    # Given clues are given.
    for i, j in givens:
        model.Add(squares[i, j] == 1)

    # Row constraints must be satisfied.
    for i, clues in enumerate(row_clues):
        line = [squares[i, j] for j in range(num_columns)]
        constrain_line(model, line, clues)

    # Column constraints must be satisfied.
    for j, clues in enumerate(column_clues):
        line = [squares[i, j] for i in range(num_rows)]
        constrain_line(model, line, clues, invert=invert_columns)

    # Find a solution.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Pretty print the solution.
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):  # type: ignore[comparison-overlap]
        for i in range(num_rows):
            row = [solver.Value(squares[i, j]) for j in range(num_columns)]
            pretty_row = ["█" if filled else " " for filled in row]
            print("".join(pretty_row))
    else:
        print("No solution found")

    print()


RED1 = [
    [1],
    [3],
    [4],
    [4],
    [3],
    #
    [1, 3],
    [2, 3],
    [5],
    [8],
    [2, 6],
    #
    [3, 4, 2],
    [2, 2, 2],
    [5],
    [4, 8],
    [9, 7],
    #
    [14, 1, 3],
    [9, 1, 3],
    [1, 3, 1, 7],
    [6, 2, 7],
    [13, 7],
    #
    [13, 7],
    [13, 7],
    [13, 7],
    [13, 7],
    [13, 7],
    #
    [13, 7],
    [11, 6],
    [8, 4],
    [5, 2],
    [2, 1],
]

RED2 = [
    [4, 25],
    [2, 4, 22],
    [1, 3, 6, 12, 2],
    [5, 2, 3, 11, 1],
    [7, 3, 10, 1],
    #
    [21, 3],
    [4, 1, 3, 7, 4],
    [5, 3, 5, 5],
    [12, 1, 6],
    [2, 2, 4, 7],
    #
    [8, 8],
    [3, 3, 7],
    [6, 8],
    [5, 3],
    [2, 2, 3],
    #
    [10],
    [8],
    [5],
    [1, 2],
    [],
    #
    [3],
    [2, 1],
    [2],
    [1],
    [2, 1],
    #
    [2, 2],
    [1],
    [1, 1, 1],
    [2, 2, 1],
    [2],
]

RED3 = [
    [17, 4],
    [17, 1, 3],
    [14, 2, 3],
    [12, 1, 3],
    [9, 2, 2, 1],
    #
    [2, 7, 1, 4],
    [4, 4, 3, 1, 1],
    [1, 3, 2, 1, 3, 1, 1],
    [3, 2, 3, 2],
    [3, 1, 2, 3, 1],
    #
    [2, 5, 2, 1, 3, 1],
    [1, 8, 1, 2, 3],
    [1, 11, 1, 1],
    [2, 1, 2, 6, 4, 2],
    [1, 1, 4, 3, 1],
    #
    [2, 2, 1, 3, 2],
    [1, 2, 3, 1],
    [1, 2, 1, 3],
    [4, 2, 1],
    [3, 1, 2],
    #
    [3, 2, 1],
    [3, 1, 1, 2],
    [3, 2, 1],
    [3, 2, 2],
    [3, 2, 1],
    #
    [4, 3, 2],
    [2, 3, 3, 1],
    [3, 4, 4],
    [6, 1, 1],
    [4],
]

BLUE1 = [
    [26],
    [1, 25],
    [1, 22, 1],
    [14, 7, 1],
    [1, 13, 8],
    #
    [2, 12, 8],
    [22],
    [1, 21],
    [2, 1, 20],
    [1, 18],
    #
    [2, 1, 11, 4],
    [2, 10, 4],
    [2, 1, 14],
    [3, 1, 13],
    [2, 1, 11, 1],
    #
    [2, 9],
    [1, 3, 11],
    [5, 11],
    [6, 12],
    [7, 12],
    #
    [5, 13],
    [5, 9, 4],
    [3, 1, 3, 6, 3],
    [3, 4, 5, 5],
    [3, 10, 6],
    #
    [3, 8, 7],
    [4, 9, 7],
    [3, 17],
    [2, 17],
    [14, 1],
]


BLUE2 = [
    [3, 2, 2, 1, 1, 11],
    [3, 3, 2, 1, 2, 11],
    [3, 4, 2, 3, 6, 2],
    [3, 4, 3, 6, 1],
    [3, 7, 1, 6],
    #
    [3, 4, 4, 7],
    [3, 2, 6, 6],
    [3, 8, 3, 1],
    [3, 8, 2, 1],
    [3, 8, 2, 2],
    #
    [3, 6, 1, 1],
    [3, 3, 2, 6],
    [3, 1, 4, 5],
    [3, 4, 2, 5],
    [6, 7, 1, 4],
    #
    [6, 9, 2, 4],
    [6, 1, 9, 1, 3],
    [6, 4, 9, 2, 3],
    [4, 6, 9, 1, 2],
    [2, 1, 3, 9, 2, 2],
    #
    [4, 1, 2, 11, 1],
    [6, 5, 9, 2],
    [7, 6, 6, 4],
    [6, 6, 4, 6],
    [1, 7, 6, 1, 8],
    #
    [1, 1, 3, 6, 10],
    [2, 1, 1, 4, 12],
    [2, 1, 2, 1, 1, 14],
    [3, 1, 3, 16],
    [3, 4, 18],
]

BLUE3 = [
    [30],
    [30],
    [15, 14],
    [14, 14],
    [13, 1, 4],
    #
    [11, 1, 2, 4],
    [11, 1, 1, 3],
    [10, 2, 1, 3],
    [10, 3, 1, 3],
    [10, 3, 1, 2],
    #
    [9, 4, 2, 2],
    [9, 4, 1, 2],
    [15, 1, 1],
    [5, 6, 1, 1],
    [6, 3, 2, 1],
    #
    [7, 3, 2],
    [5, 5],
    [3, 19],
    [2, 1, 5],
    [1, 3, 4, 1, 1],
    #
    [4, 4, 1, 2],
    [1, 7, 2, 2, 2],
    [10, 1, 1, 3],
    [12, 1, 3],
    [11, 1, 4],
    #
    [11, 15],
    [12, 16],
    [13, 16],
    [30],
    [30],
]

L31_ROWS = [
    [2],
    [1, 2, 1],
    [6],
    [4],
    [2, 2, 2, 2],
    [2, 2, 2, 2],
    [1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1],
    [6, 6, 6, 6],
    [1, 4, 4, 1],
    [1, 2, 1, 2, 2, 2, 2, 1, 2, 1],
    [6, 2, 6],
    [1, 1, 1, 2, 1, 1, 1],
    [1, 4, 6, 4, 1],
    [3, 1, 4, 1, 3],
    [2, 2, 2, 2, 2, 2],
    [1, 3, 1, 1, 3, 1],
    [4, 2, 2, 4],
    [4, 4, 4],
    [1, 1, 4, 1, 1],
    [5, 2, 5],
    [3, 4, 3],
    [2, 4, 2],
    [6],
]

L31_COLS = [
    [2, 2],
    [1, 1, 2, 2],
    [7, 1, 1, 2],
    [2, 1, 6, 1, 1],
    [1, 1, 1, 6],
    [2, 2, 1, 1, 1, 1],
    [2, 2, 1, 2],
    [2, 1, 2, 2, 1],
    [3, 2, 2],
    [4, 1],
    [4],
    [3],
    [2, 1, 2, 1, 2, 1, 1],
    [3, 3, 2, 3],
    [4, 4, 6],
    [4, 4, 6],
    [3, 3, 2, 3],
    [2, 1, 2, 1, 2, 1, 1],
    [3],
    [4],
    [4, 1],
    [3, 2, 2],
    [2, 1, 2, 2, 1],
    [2, 2, 1, 2],
    [2, 2, 1, 1, 1, 1],
    [1, 1, 1, 6],
    [2, 1, 6, 1, 1],
    [7, 1, 1, 2],
    [1, 1, 2, 2],
    [2, 2],
]


def main() -> None:
    solve_puzzle(L31_ROWS, L31_COLS)
    # solve_puzzle(RED1, BLUE3, invert_columns=True)
    # solve_puzzle(RED2, BLUE1, invert_columns=True)
    # solve_puzzle(RED3, BLUE2, invert_columns=True)


if __name__ == "__main__":
    main()
