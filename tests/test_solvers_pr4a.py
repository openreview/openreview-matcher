# TODO: This is a leftover module from the days of David. Clean this up / make it readable!
from collections import namedtuple
import pytest
import numpy as np
from matcher.solvers import PR4ASolver
from conftest import assert_arrays

encoder = namedtuple('Encoder', ['aggregate_score_matrix', 'constraint_matrix'])

def check_solution(solver, expected_cost):
    assert solver.optimal_cost == solver.cost, "Minimum cost solution is not the sum of the flows * unit cost in result matrix"
    assert solver.cost == expected_cost,  "Lowest cost solution should have cost = {}".format(expected_cost)

def test_solvers_pr4a_random():
    '''When costs are all zero, compute random assignments'''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    solver_A = PR4ASolver(
        [1,1,1,1],
        [2,2,2,2],
        [2,2,2],
        encoder(aggregate_score_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    print(res_A)
    assert res_A.shape == (3,4)

def test_solvers_pr4a_custom_supply():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 1, max: [2,1,3,1] papers respectively.
    Each papers needs 2 reviews.
    No constraints.
    Purpose: Assert that reviewers are assigned papers correctly based on their supply.
    """
    aggregate_score_matrix_A = np.transpose(
        np.array(
            [
                [0.2, 0.1, 0.4],
                [0.5, 0.2, 0.3],
                [0.2, 0.0, 0.6],
                [0.7, 0.9, 0.3],
            ]
        )
    )
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2, 2, 2]
    solver_A = PR4ASolver(
        [1, 1, 1, 1],
        [2, 1, 3, 1],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result, demands)

def test_solver_pr4a_no_0_score_assignment():
    """
    Tests 5 papers, 4 reviewers.
    Reviewers review min: 1, max: 3 papers.
    Each paper needs 2 reviews.
    Reviewer 0 cannot review paper 1.
    Purpose: Assert that an assignment is never made for 0 or less score
    """
    aggregate_score_matrix = np.transpose(
        np.array(
            [
                [-1, 1, 1, 0, 1],
                [1, 0, -1, 0, 1],
                [0, 1, 1, 1, 0],
                [1, 1, 1, 1, 0],
            ]
        )
    )
    constraint_matrix = np.transpose(
        np.array(
            [
                [0, -1, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0],
            ]
        )
    )

    solver = PR4ASolver(
        [1, 1, 1, 1],
        [3, 3, 3, 3],
        [2, 2, 2, 2, 2],
        encoder(aggregate_score_matrix, constraint_matrix),
    )

    res = solver.solve()
    assert res.shape == (5, 4)
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for i in range(nrows):
        for j in range(ncols):
            assert not (
                aggregate_score_matrix[i, j] <= 0 and res[i, j] > 0
            ), "Solution violates the rule for not making less than 0 score assignments at [{},{}]".format(
                i, j
            )
