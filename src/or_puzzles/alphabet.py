#!/usr/bin/env python3


import string

from ortools.sat.python import cp_model

ALPHABET = string.ascii_lowercase


class Solver:
    def __init__(self) -> None:
        self.model = cp_model.CpModel()
        self.letters = {k: self.model.new_int_var(1, 26, k) for k in ALPHABET}

    def constrain(self, word: str, total: int) -> None:
        self.model.add(sum(self.letters[c] for c in word) == total)

    def all_constraints(self) -> None:
        self.model.add_all_different(self.letters.values())
        self.model.add(self.letters["j"] < 10)

        self.constrain("ariary", 111)
        self.constrain("birr", 83)
        self.constrain("dalasi", 104)
        self.constrain("dobra", 90)
        self.constrain("florin", 100)
        self.constrain("forint", 95)
        self.constrain("franc", 97)
        self.constrain("gourde", 98)
        self.constrain("guarani", 162)
        self.constrain("hryvnia", 106)
        self.constrain("kip", 24)
        self.constrain("krone", 65)
        self.constrain("kwanza", 102)
        self.constrain("kyat", 35)
        self.constrain("naira", 111)
        self.constrain("ngultrum", 143)
        self.constrain("quetzal", 99)
        self.constrain("ringgit", 139)
        self.constrain("sheqel", 65)
        self.constrain("taka", 57)
        self.constrain("tugrik", 100)
        self.constrain("zloty", 43)

    def solve(self) -> None:
        solver = cp_model.CpSolver()
        status = solver.solve(self.model)
        assert status == cp_model.OPTIMAL

        for c in ALPHABET:
            print(f"{c} = {solver.value(self.letters[c])}")

        for word in (
            "bottlecap",
            "crindar",
            "darsek",
            "shanix",
            "vinderbucks",
            "woolong",
        ):
            value = sum(solver.value(self.letters[c]) for c in word)
            print(f"{word} should be {value}")


def solve_puzzle() -> None:
    model = Solver()
    model.all_constraints()
    model.solve()


if __name__ == "__main__":
    solve_puzzle()
