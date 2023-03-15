from collections import namedtuple
import pytest
from matcher.core import SolverException
import numpy as np
from matcher.solvers import FairIR
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
    solver_A = FairIR(
        [1,1,1,1],
        [2,2,2,2],
        [2,2,2],
        encoder(aggregate_score_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    print(res_A)
    assert res_A.shape == (3,4)

def test_solvers_pr4a_simple_attribute_constraint():
    '''Test constraint that each paper must have reviewer[3] as a reviewer'''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    solver_A = FairIR(
        [0,0,0,0],
        [2,2,2,3],
        [2,2,2],
        encoder(aggregate_score_matrix_A, constraint_matrix),
        attr_constraints=[{
            'name': 'Seniority',
            'comparator': '<=',
            'bound': 1,
            'members': [3]
        }]
    )
    res_A = solver_A.solve()
    print(res_A)
    for paper_idx in range(3):
        assert res_A[paper_idx][3] == 1
    assert res_A.shape == (3,4)

def test_solvers_pr4a_structure_attribute_constraint():
    '''Test constraint that each paper must have reviewer[3] as a reviewer as well as obey similarity structure'''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0.5, 0, 0],
        [0, 0.5, 0],
        [0, 0, 0.5],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    solver_A = FairIR(
        [0,0,0,0],
        [2,2,2,3],
        [2,2,2],
        encoder(aggregate_score_matrix_A, constraint_matrix),
        attr_constraints=[{
            'name': 'Seniority',
            'comparator': '<=',
            'bound': 1,
            'members': [3]
        }]
    )
    res_A = solver_A.solve()
    print(res_A)
    for paper_idx in range(3):
        assert res_A[paper_idx][3] == 1

    assert res_A[0][0] == 1
    assert res_A[1][1] == 1
    assert res_A[2][2] == 1
    assert res_A.shape == (3,4)

def test_solvers_pr4a_attribute_constraint_over_similarity():
    '''Test multiple constraint sets that go against highest similarity'''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0.5, 0, 0],
        [0.5, 0, 0],
        [0, 0, 0.5],
        [0, 0, 0.5]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    solver_A = FairIR(
        [0,0,0,0],
        [2,2,2,3],
        [2,2,2],
        encoder(aggregate_score_matrix_A, constraint_matrix),
        attr_constraints=[{
            'name': 'constr1',
            'comparator': '<=',
            'bound': 1,
            'members': [0, 1]
        },
        {
            'name': 'constr2',
            'comparator': '<=',
            'bound': 1,
            'members': [2, 3]
        }]
    )
    res_A = solver_A.solve()
    print(res_A)
    assert res_A.shape == (3,4)
    assert bool(res_A[0][0] == 1) ^ bool(res_A[0][1] == 1)
    assert bool(res_A[2][2] == 1) ^ bool(res_A[2][3] == 1)

def test_solvers_pr4a_conflict():
    '''When reviewer[1] has conflicts with all papers, assert that no assignments were made to them'''
    conflicted_reviewer_idx = 1

    aggregate_score_matrix_A = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0],
        [-1, -1, -1],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    solver_A = FairIR(
        [1,1,1,1],
        [2,2,2,2],
        [2,2,2],
        encoder(aggregate_score_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    print(res_A)
    assert res_A.shape == (3,4)
    for paper_idx in range(3):
        assert res_A[paper_idx][conflicted_reviewer_idx] == 0

def test_solvers_pr4a_zero_scores():
    '''No similarities while not allowing zero score assignments will raise an exception'''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    with pytest.raises(SolverException, match=r"4 members found with no affinity scores while not allowing zero score assignments"):
            assert FairIR(
                    [1, 1, 1, 1],
                    [2, 2, 2, 2],
                    [2,2,2],
                    encoder(aggregate_score_matrix_A, constraint_matrix),
                    allow_zero_score_assignments=False
                )

def test_solvers_pr4a_custom_demands():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 1, max: 2 papers.
    Papers need [2,1,3] reviews.
    No constraints.
    Purpose: Assert that papers demands are matched.

    Issue: PR4A does not support custom demands
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
    demands = [2, 1, 3]

    with pytest.raises(SolverException, match=r'PR4A does not support custom paper demands, all demands must be the same'):
            assert FairIR(
                    [1, 1, 1, 1],
                    [2, 2, 2, 2],
                    demands,
                    encoder(aggregate_score_matrix_A, constraint_matrix),
                )

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
    solver_A = FairIR(
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

    solver = FairIR(
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