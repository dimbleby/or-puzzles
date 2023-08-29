#!/usr/bin/env python3
from __future__ import annotations

from ortools.sat.python import cp_model


def solve_puzzle() -> None:
    """Solve a puzzle"""
    # Prepare a model.
    model = cp_model.CpModel()

    # Create variables.
    [canaries, spain, switzerland, czech_republic, bulgaria] = range(5)

    nests = [model.NewIntVar(0, 4, f"nests{i}") for i in range(5)]
    [chimney, hedge, house, lake, straw] = nests

    breeds = [model.NewIntVar(0, 4, f"breeds{i}") for i in range(5)]
    [finch, mallard, starling, swallow, woodpecker] = breeds

    foods = [model.NewIntVar(0, 4, f"foods{i}") for i in range(5)]
    [bread, cake, cookies, croissants, scones] = foods

    activities = [model.NewIntVar(0, 4, f"activities{i}") for i in range(5)]
    [bird_baths, collecting, pecking, stealing, squawking] = activities

    hometowns = [model.NewIntVar(0, 4, f"hometowns{i}") for i in range(5)]
    [barking, camden, ealing, hounslow, kensington] = hometowns

    model.AddAllDifferent(nests)
    model.AddAllDifferent(breeds)
    model.AddAllDifferent(foods)
    model.AddAllDifferent(activities)
    model.AddAllDifferent(hometowns)

    # collecting-twigs next to kensington
    model.AddAbsEquality(1, collecting - kensington)

    # bird-baths next to brentford (which is in hounslow)
    model.AddAbsEquality(1, bird_baths - hounslow)

    # spain and lakes
    model.Add(lake == spain)

    # finch and squawking
    model.Add(finch == squawking)

    # croissants and pecking
    model.Add(croissants == pecking)

    # woodpeckers in tenerife
    model.Add(woodpecker == canaries)

    # straw, birdbath
    model.Add(straw == bird_baths)

    # chocolate chip cookies, switzerland
    model.Add(cookies == switzerland)

    # shiny things, ealing
    model.Add(stealing == ealing)

    # chimney stack one east of hedge
    model.Add(chimney == hedge + 1)

    # starling, scones
    model.Add(starling == scones)

    # hedges, cakes
    model.Add(hedge == cake)

    # mallard, barking
    model.Add(mallard == barking)

    # swallow, house
    model.Add(swallow == house)

    # We want to know everything...
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        print()
        print("nests:", [solver.Value(nests[i]) + 1 for i in range(5)])
        print("breeds:", [solver.Value(breeds[i]) + 1 for i in range(5)])
        print("foods:", [solver.Value(foods[i]) + 1 for i in range(5)])
        print("activities:", [solver.Value(activities[i]) + 1 for i in range(5)])
        print("hometowns:", [solver.Value(hometowns[i]) + 1 for i in range(5)])


if __name__ == "__main__":
    solve_puzzle()
