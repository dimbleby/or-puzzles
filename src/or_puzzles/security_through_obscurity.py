#!/usr/bin/env python3
# Number the grid as:
#
#  0  1  2  3  4  5
#  6  7  8  9 10 11
# 12 13 14 15 16 17
# 18 19 20 21 22 23
# 24 25 26 27 28 29
# 30 31 32 33 34 35
#
# row 0 at the top, column 0 at the left: so square == 6 * row + col
#
# Number the cards 0 through 39, then:
#
# - the face value of a card is card % 10
# - the suit of a card is card // 10
from __future__ import annotations

from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from collections.abc import Iterable

KNIGHT_MOVES = [
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (-2, -1),
    (-2, 1),
    (2, -1),
    (2, 1),
]
SUITS = ["C", "D", "H", "S"]


def neighbours(square: int) -> Iterable[int]:
    row = square // 6
    col = square % 6
    for dr, dc in KNIGHT_MOVES:
        new_row = row + dr
        if not 0 <= new_row < 6:
            continue

        new_col = col + dc
        if not 0 <= new_col < 6:
            continue

        new_square = 6 * new_row + new_col
        yield new_square


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, cards: list[cp_model.IntVar]) -> None:
        super().__init__()
        self.cards = cards

    def pretty(self, card: cp_model.IntVar) -> str:
        value = self.Value(card)
        face = value % 10
        suit = SUITS[value // 10]
        return f"{face}{suit}"

    def on_solution_callback(self) -> None:
        for row in range(6):
            cards = self.cards[row * 6 : (row + 1) * 6]
            pretty_cards = [f"{self.pretty(card)}" for card in cards]
            print(" ".join(pretty_cards))

        pretty_pin = [f"{self.pretty(card)}" for card in self.cards[-4:]]
        pin = " ".join(pretty_pin)
        print(f"PIN: {pin}\n")


def solve() -> None:
    model = cp_model.CpModel()

    # Make a knights tour.
    route = [model.NewIntVar(0, 35, f"route_{i}") for i in range(36)]
    next_hop = [model.NewIntVar(0, 35, f"next_hop_{i}") for i in range(36)]

    model.AddAllDifferent(route)
    model.AddAllDifferent(next_hop)

    for i in range(36):
        candidates = neighbours(i)
        domain = cp_model.Domain.FromValues(list(candidates))
        model.AddLinearExpressionInDomain(next_hop[i], domain)
        model.AddElement(route[i - 1], next_hop, route[i])

    # What is the sequence of cards that we lay?
    card_sequence = [model.NewIntVar(0, 39, f"seq_{i}") for i in range(36)]
    for i in range(35):
        model.Add(card_sequence[i] < card_sequence[i + 1])

    # What card is on each square?  Four extra squares for the PIN.
    cards = [model.NewIntVar(0, 39, f"card_{i}") for i in range(40)]
    model.AddAllDifferent(cards)
    for i in range(36):
        model.AddElement(route[i], cards, card_sequence[i])

    # What square is each card on?
    squares = [model.NewIntVar(0, 39, f"square_{i}") for i in range(40)]
    model.AddAllDifferent(squares)
    model.AddInverse(cards, squares)

    # Face values on each square, again with four at the end for the PIN.
    faces = [model.NewIntVar(0, 9, f"face_{i}") for i in range(40)]
    for i in range(40):
        model.AddModuloEquality(faces[i], cards[i], 10)

    # Suits on each square, again with four at the end for the PIN.
    suits = [model.NewIntVar(0, 3, f"suit_{i}") for i in range(40)]
    for i in range(40):
        model.AddDivisionEquality(suits[i], cards[i], 10)

    # One card from each suit is taken for the PIN.
    #
    # Force the order as spades, hearts, diamonds, clubs: breaking symmetry and
    # convenient for PIN extraction.
    model.Add(suits[-4] == 3)
    model.Add(suits[-3] == 2)
    model.Add(suits[-2] == 1)
    model.Add(suits[-1] == 0)

    # They all are different digits. Diamond is highest.
    model.AddAllDifferent(faces[-4:])
    model.Add(faces[-2] > faces[-1])
    model.Add(faces[-2] > faces[-3])
    model.Add(faces[-2] > faces[-4])

    # We're given some adjacent pairs.
    #
    # The constraint here is weaker than what we are told, but it's easy and sufficient.
    for card in (6, 9, 13, 18, 31, 39):
        model.Add(squares[card] < 36)
    adjacent = cp_model.Domain.FromValues([-6, -1, 1, 6])
    model.AddLinearExpressionInDomain(squares[6] - squares[9], adjacent)
    model.AddLinearExpressionInDomain(squares[13] - squares[18], adjacent)
    model.AddLinearExpressionInDomain(squares[31] - squares[39], adjacent)

    # Threes and nines in the grid are all on or orthogonally adjacent to a corner.
    for i in range(36):
        if i not in {0, 1, 4, 5, 6, 11, 24, 29, 30, 31, 34, 35}:
            model.Add(faces[i] != 3)
            model.Add(faces[i] != 9)

    # Diamond PIN is from 1975, the others aren't.
    nineteenseventyfive = cp_model.Domain.FromValues([1, 9, 7, 5])
    model.AddLinearExpressionInDomain(faces[-2], nineteenseventyfive)
    for i in (-1, -3, -4):
        model.Add(faces[i] != 1)
        model.Add(faces[i] != 9)
        model.Add(faces[i] != 7)
        model.Add(faces[i] != 5)

    # The central four squares contain one of each suit.
    model.AddAllDifferent(suits[i] for i in (14, 15, 20, 21))

    # The central four squares only contain sevens and eights.
    seven_or_eight = cp_model.Domain.FromValues([7, 8])
    for i in (14, 15, 20, 21):
        model.AddLinearExpressionInDomain(faces[i], seven_or_eight)

    # The third row from the top contains no composite numbers.
    noncomposite = cp_model.Domain.FromValues([0, 1, 2, 3, 5, 7])
    for i in range(12, 18):
        model.AddLinearExpressionInDomain(faces[i], noncomposite)

    # The fourth row from the top contains no odd numbers.
    evens = cp_model.Domain.FromValues([0, 2, 4, 6, 8])
    for i in range(18, 24):
        model.AddLinearExpressionInDomain(faces[i], evens)

    # Sum of each row is greater than the row above it.
    this_sum = sum(faces[:6])
    for r in range(1, 6):
        prev_sum = this_sum
        this_sum = sum(faces[r * 6 : (r + 1) * 6])
        model.Add(prev_sum < this_sum)

    # After the event we learned that the clue we missed was:
    #
    # Ace of clubs is in the top-left corner, six of spades is in the top-right. The
    # corners total fifteen.
    #
    # model.Add(cards[0] == 1)
    # model.Add(cards[5] == 36)
    # model.Add(sum(faces[i] for i in (0, 5, 30, 35)) == 15)
    #
    # Not having that we instead just broke left-right symmetry:
    model.Add(cards[0] < cards[5])

    # Solve.
    solution_printer = SolutionPrinter(cards)
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
    solver.Solve(model, solution_printer)


if __name__ == "__main__":
    solve()
