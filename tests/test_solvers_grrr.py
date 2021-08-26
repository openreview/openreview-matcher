from collections import namedtuple
import pytest
import numpy as np
from matcher.solvers import SolverException, GRRR
from conftest import assert_arrays

encoder = namedtuple('Encoder', ['aggregate_score_matrix', 'constraint_matrix'])

def test_solvers_grrr_random():
    '''When costs are all zero, compute random assignments'''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2,2,2]
    solver_A = GRRR(
        [0,0,0,0],
        [2,2,2,2],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3,4)
    assert solver_A.solved

    aggregate_score_matrix_B = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_B))
    solver_B = GRRR(
        [0,0,0,0],
        [2,2,2,2],
        demands,
        encoder(aggregate_score_matrix_B, constraint_matrix)
    )
    res_B = solver_B.solve()
    assert res_B.shape == (3,4)
    assert solver_B.solved

    # ensure that the affinity matrices are random
    # (i.e. overwhelmingly likely to be different)
    assert not np.array_equal(solver_A.affinity_matrix, solver_B.affinity_matrix)
    result_A = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result_A, demands)
    result_B = [assignments for assignments in np.sum(res_B, axis=1)]
    assert_arrays(result_B, demands)

def test_solvers_grrr_custom_supply():
    '''
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: [2,1,2,1] papers respectively.
    Each papers needs 2 reviews.
    No constraints.
    Purpose: Assert that reviewers are assigned papers correctly based on their supply.
    '''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0.2, 0.1, 0.4],
        [0.5, 0.2, 0.3],
        [0.2, 0.0, 0.6],
        [0.7, 0.9, 0.3]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2,2,2]
    solver_A = GRRR(
        [0,0,0,0],
        [2,1,2,1],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3,4)
    result_demands = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result_demands, demands)
    result_supply = [assignments for assignments in np.sum(res_A, axis=0)]
    assert_arrays(result_supply, [2,1,2,1])

def test_solver_grrr_fail_with_supply_mins():
    '''
    Test to ensure that the GRRR solver's 'solved' attribute is correctly set
    when we pass in reviewer minimums. This setting is not supported by GRRR.
    '''
    num_papers = 3
    num_reviewers = 4
    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix))

    minimums = [1] * num_reviewers
    maximums = [2] * num_reviewers
    demands = [2] * num_papers

    solver = GRRR(
        minimums,
        maximums,
        demands,
        encoder(aggregate_score_matrix, constraint_matrix)
    )

    with pytest.raises(SolverException,
                       match=r'GRRR does not currently support minimum values for number of papers per reviewer'):
        solver.solve()

    assert not solver.solved

def test_solver_grrr_fail_with_custom_demands():
    '''
    Test to ensure that the GRRR solver's 'solved' attribute is correctly set
    when we pass in non-uniform paper demands. This setting is not supported by GRRR.
    '''

    num_papers = 3
    num_reviewers = 4
    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix))

    minimums = [0] * num_reviewers
    maximums = [2] * num_reviewers
    demands = [2,1,2]

    solver = GRRR(
        minimums,
        maximums,
        demands,
        encoder(aggregate_score_matrix, constraint_matrix)
    )

    with pytest.raises(SolverException,
                       match=r'GRRR does not currently support different demands for each paper'):
        solver.solve()

    assert not solver.solved

def test_solver_grrr_impossible_constraints():
    '''
    Test to ensure that the GRRR solver's 'solved' attribute is correctly set
    when no solution is possible due to constraints.
    '''

    # 20 papers, 5 reviewers
    num_papers = 20
    num_reviewers = 5
    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = -1 * np.ones((num_papers, num_reviewers)) # all pairs are constrained! should be impossible

    minimums = [0] * 5
    maximums = [20] * 5
    demands = [3] * 20

    solver = GRRR(
        minimums,
        maximums,
        demands,
        encoder(aggregate_score_matrix, constraint_matrix)
    )

    with pytest.raises(SolverException):
        solver.solve()

    assert not solver.solved

def test_solver_grrr_respects_constraints():
    '''
    Tests 5 papers, 4 reviewers.
    Reviewers review min: 0, max: 4 papers.
    Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 2,3
             2: cannot review papers 2,3
             3: cannot review papers 0,1
    All scores set to 1 so that any match that does not violate constraints is optimal.
    Purpose:  Honors constraints in its solution
    '''
    aggregate_score_matrix = np.transpose(np.array([
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1]]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0, 0, 0],
        [0, 0, -1, -1, 0],
        [0, 0, -1, -1, 0],
        [-1, -1, 0, 0, 0]]))

    solver = GRRR(
        [0,0,0,0],
        [4,4,4,4],
        [2,2,2,2,2],
        encoder(aggregate_score_matrix, constraint_matrix)
    )

    res = solver.solve()
    assert res.shape == (5, 4)
    assert solver.solved
    # make sure result does not violate constraints
    nrows, ncols = res.shape if len(res.shape) == 2 else (0,0)
    for i in range(nrows):
        for j in range(ncols):
            assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)

def test_solver_grrr_respect_constraints_2():
    '''
    Tests 5 papers, 4 reviewers.
    Reviewers review min: 0, max: 3 papers.
    Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 0,3
             2: cannot review papers 3,4
             3: cannot review papers 1,2
    Purpose: Honors constraints in its solution
    '''
    aggregate_score_matrix = np.transpose(np.array([
        [-10, 1, 1, -10, -10],
        [-100, -10, -10, -100, 1],
        [1, -10, -10, -100, -100],
        [-10, -100, -100, -10, -10]]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0, 0, 0],
        [-1, 0, 0, -1, 0],
        [0, 0 , 0, -1, -1],
        [0, -1,-1, 0, 0]]))

    solver = GRRR(
        [0,0,0,0],
        [3,3,3,3],
        [2,2,2,2,2],
        encoder(aggregate_score_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (5, 4)
    assert solver.solved
    # make sure result does not violate constraints
    nrows, ncols = res.shape if len(res.shape) == 2 else (0,0)
    for i in range(nrows):
        for j in range(ncols):
            assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)

def ef1(allocation, affinities):
    '''
    Checks if the allocation is envy-free up to 1 item (EF1).
    Not a test, but is a criterion for the remaining tests.

    Args:
        allocation - (2d numpy array) assignment of reviewers to papers
        affinities - (2d numpy array) affinities between papers and reviewers

    Returns:
        True if the allocation satisfies the EF1 criterion, otherwise False.
    '''
    n = allocation.shape[0]
    for i in range(n):
        # i's value for self
        i_value_i = np.sum(allocation[i, :] * affinities[i, :])
        for j in range(n):
            # i's lowest value for j, minus a good
            i_value_j_up_to_1 = np.sum(allocation[j, :] * affinities[i, :]) - np.max(allocation[j, :] * affinities[i, :])
            if i_value_j_up_to_1 > i_value_i:
                return False
    return True

def test_solver_grrr_envy_free_up_to_one_item():
    '''
    Tests 10 papers, 15 reviewers, for 10 random affinity matrices.
    Reviewers review min: 0, max: 3 papers.
    Each paper needs 3 reviews.
    No constraints.
    Purpose: Ensure that the GRRR solver returns allocations that are envy-free up to 1 item.
    '''
    num_papers = 10
    num_reviewers = 15

    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix))

    minimums = [0] * num_reviewers
    maximums = [3] * num_reviewers
    demands = [3] * num_papers

    for _ in range(10):
        solver = GRRR(
            minimums,
            maximums,
            demands,
            encoder(aggregate_score_matrix, constraint_matrix)
        )
        res = solver.solve()

        assert res.shape == (10, 15)
        assert solver.solved
        assert ef1(res, solver.affinity_matrix.transpose())

def test_solver_grrr_envy_free_up_to_one_item_constrained():
    '''
    Tests 10 papers, 15 reviewers, for 10 random affinity matrices.
    Reviewers review min: 0, max: 3 papers.
    Each paper needs 3 reviews.
    Constraints chosen at random, with a 10% chance of any given constraint.
    Purpose: Ensure that the GRRR solver returns allocations that are envy-free up to 1 item and satisfy constraints.
    '''
    num_papers = 10
    num_reviewers = 15

    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    shape = np.shape(aggregate_score_matrix)

    minimums = [0] * num_reviewers
    maximums = [3] * num_reviewers
    demands = [3] * num_papers

    for _ in range(10):
        constraint_matrix = np.where(
            np.random.rand(shape[0], shape[1]) > 0.1,
            np.zeros(shape),
            -1 * np.ones(shape))

        solver = GRRR(
            minimums,
            maximums,
            demands,
            encoder(aggregate_score_matrix, constraint_matrix)
        )
        res = solver.solve()

        assert res.shape == (10, 15)
        assert solver.solved
        assert ef1(res, solver.affinity_matrix.transpose())

        nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
        for i in range(nrows):
            for j in range(ncols):
                assert not (constraint_matrix[i, j] == -1 and res[
                    i, j] > 0), "Solution violates constraint at [{},{}]".format(i, j)