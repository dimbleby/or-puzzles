#!/usr/bin/env python3
from __future__ import annotations

from ortools.sat.python import cp_model


def solve_puzzle() -> None:
    """Solve a puzzle"""
    # Prepare a model.
    model = cp_model.CpModel()

    # Create variables.
    [canaries, spain, switzerland, _czech_republic, _bulgaria] = range(5)

    nests = [model.new_int_var(0, 4, f"nests{i}") for i in range(5)]
    [chimney, hedge, house, lake, straw] = nests

    breeds = [model.new_int_var(0, 4, f"breeds{i}") for i in range(5)]
    [finch, mallard, starling, swallow, woodpecker] = breeds

    foods = [model.new_int_var(0, 4, f"foods{i}") for i in range(5)]
    [_bread, cake, cookies, croissants, scones] = foods

    activities = [model.new_int_var(0, 4, f"activities{i}") for i in range(5)]
    [bird_baths, collecting, pecking, stealing, squawking] = activities

    hometowns = [model.new_int_var(0, 4, f"hometowns{i}") for i in range(5)]
    [barking, _camden, ealing, hounslow, kensington] = hometowns

    model.add_all_different(nests)
    model.add_all_different(breeds)
    model.add_all_different(foods)
    model.add_all_different(activities)
    model.add_all_different(hometowns)

    # collecting-twigs next to kensington
    model.add_abs_equality(1, collecting - kensington)

    # bird-baths next to brentford (which is in hounslow)
    model.add_abs_equality(1, bird_baths - hounslow)

    # spain and lakes
    model.add(lake == spain)

    # finch and squawking
    model.add(finch == squawking)

    # croissants and pecking
    model.add(croissants == pecking)

    # woodpeckers in tenerife
    model.add(woodpecker == canaries)

    # straw, birdbath
    model.add(straw == bird_baths)

    # chocolate chip cookies, switzerland
    model.add(cookies == switzerland)

    # shiny things, ealing
    model.add(stealing == ealing)

    # chimney stack one east of hedge
    model.add(chimney == hedge + 1)

    # starling, scones
    model.add(starling == scones)

    # hedges, cakes
    model.add(hedge == cake)

    # mallard, barking
    model.add(mallard == barking)

    # swallow, house
    model.add(swallow == house)

    # We want to know everything...
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):  # type: ignore[comparison-overlap]
        print()
        print("nests:", [solver.Value(nests[i]) + 1 for i in range(5)])
        print("breeds:", [solver.Value(breeds[i]) + 1 for i in range(5)])
        print("foods:", [solver.Value(foods[i]) + 1 for i in range(5)])
        print("activities:", [solver.Value(activities[i]) + 1 for i in range(5)])
        print("hometowns:", [solver.Value(hometowns[i]) + 1 for i in range(5)])


if __name__ == "__main__":
    solve_puzzle()
