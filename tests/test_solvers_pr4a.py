# TODO: This is a leftover module from the days of David. Clean this up / make it readable!
from collections import namedtuple
import pytest
import numpy as np
from matcher.solvers import PR4ASOLVER

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
    solver_A = PR4ASOLVER(
        [1,1,1,1],
        [2,2,2,2],
        [2,2,2],
        encoder(aggregate_score_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    print(res_A)
    assert res_A.shape == (3,4)
    assert 0 == 1
