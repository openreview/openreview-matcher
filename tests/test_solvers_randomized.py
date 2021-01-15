import pytest
from collections import namedtuple
import numpy as np
from matcher.solvers import SolverException, RandomizedSolver

encoder = namedtuple('Encoder', ['cost_matrix', 'constraint_matrix', 'prob_limit_matrix'])

def check_sampled_solution(solver):
    ''' Performs basic checks on the validity of a sampled assignment '''
    pap_loads = np.sum(solver.flow_matrix, axis=1)
    rev_loads = np.sum(solver.flow_matrix, axis=0)
    assert np.all(np.logical_or(solver.flow_matrix == 0, solver.flow_matrix == 1)), 'Sampled assignments should be integral'
    assert (np.all(pap_loads == np.array(solver.demands)) and
            np.all(np.logical_and(rev_loads <= np.array(solver.maximums), rev_loads >= np.array(solver.minimums)))
            ), 'Sampled assignment should be in legal polytope'
    assert np.all(np.where(solver.constraint_matrix == -1, solver.flow_matrix == 0, True)), 'Sampled assignment should obey constraint matrix'

def check_test_solution(solver, T=1000, tol=1e-1):
    '''
    Takes several samples and performs basic checks on the correctness of the fractional assignment
    and the sampled assignments. T = number of samples, tol = tolerance for the mean matrix
    '''
    solver.solve()
    assert solver.solved, 'Problem should be solvable'

    pap_loads = np.sum(solver.fractional_assignment_matrix, axis=1)
    rev_loads = np.sum(solver.fractional_assignment_matrix, axis=0)
    assert (np.all(pap_loads == np.array(solver.demands)) and
            np.all(np.logical_and(rev_loads <= np.array(solver.maximums), rev_loads >= np.array(solver.minimums))) and
            np.all(np.logical_and(solver.fractional_assignment_matrix <= 1, solver.fractional_assignment_matrix >= 0))
            ), 'Fractional assignment should be in legal polytope'
    assert (np.all(np.where(solver.constraint_matrix == -1, solver.fractional_assignment_matrix == 0, True)) and
            np.all(np.where(solver.constraint_matrix == 1, solver.fractional_assignment_matrix == solver.prob_limit_matrix, True))
            ), 'Fractional assignment should obey constraint matrix'

    for i in range(T):
        if i == 0:
            mean_matrix = solver.flow_matrix
        else:
            solver.sample_assignment()
            mean_matrix += solver.flow_matrix
        check_sampled_solution(solver)
    mean_matrix /= T

    assert np.all(np.abs(mean_matrix - solver.fractional_assignment_matrix) < tol), 'Mean sampled solution should be close to fractional assignment'


def test_basic():
    ''' Simple test for basic functionality '''
    S = np.transpose(np.array([
        [1, 0.1],
        [1, 1],
        [0.3, 0.6],
        [0.5, 0.8]
    ]))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 0.75)
    solver = RandomizedSolver(
        [0,0,0,0],
        [1,1,1,1],
        [2,2],
        encoder(-S, M, Q)
    )

    check_test_solution(solver)
    # verify correct solution
    solution = np.transpose(np.array([
        [0.75, 0.25],
        [0.75, 0.25],
        [0.25, 0.75],
        [0.25, 0.75]
    ]))
    assert np.all(solver.fractional_assignment_matrix == solution), 'Fractional assignment should be correct'


def test_bad_limits():
    ''' Test for error-checking the probability limits '''
    S = np.transpose(np.array([
        [1, 0.1],
        [1, 1],
        [0.3, 0.6],
        [0.5, 0.8]
    ]))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 0.75)

    Q[1, 1] = -1
    try:
        solver = RandomizedSolver(
            [0,0,0,0],
            [1,1,1,1],
            [2,2],
            encoder(-S, M, Q)
        )
        assert False # should throw
    except SolverException:
        pass

    Q[1, 1] = 1.5 try:
        solver = RandomizedSolver(
            [0,0,0,0],
            [1,1,1,1],
            [2,2],
            encoder(-S, M, Q)
        )
        assert False # should throw
    except SolverException:
        pass


def test_different_supply_demand():
    ''' Test for custom supplies and demands '''
    S = np.transpose(np.array([
        [1, 0.1, 0.5],
        [1, 1, 0.5],
        [0.3, 0.6, 0.5],
        [0.5, 0.8, 0.5]
    ]))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 0.75)

    solver = RandomizedSolver(
        [0,1,1,0],
        [1,3,2,1],
        [3,2,1],
        encoder(-S, M, Q)
    )
    check_test_solution(solver)


def test_reviewer_minimums():
    ''' Ensure that reviewer minimums are maintained even when it increases cost '''
    S = np.transpose(np.array([
        [0, 0, 0],
        [1.0, 1.0, 1.0]
    ]))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 1.0)

    solver = RandomizedSolver(
        [1,1],
        [3,3],
        [1,1,1],
        encoder(-S, M, Q)
    )
    solver.solve()
    check_sampled_solution(solver)


def test_impossible_constraints():
    ''' Test when problem cannot be solved due to probability constraints '''
    S = np.transpose(np.array([
        [1, 0.1, 0.5],
        [1, 1, 0.5],
        [0.3, 0.6, 0.5],
        [0.5, 0.8, 0.5]
    ]))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 0.75)
    Q[0, :] = 0 # no probability on first paper

    solver = RandomizedSolver(
        [0,0,0,0],
        [3,3,3,3],
        [2,2,2],
        encoder(-S, M, Q)
    )
    solver.solve()
    assert not solver.solved


def test_fractional_reviewer_load():
    ''' Test that sampling works correctly if some reviewer loads are fractional '''
    S = np.ones((3, 3))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 0.4)

    solver = RandomizedSolver(
        [0,0,0],
        [2,2,2],
        [1,1,1],
        encoder(-S, M, Q)
    )
    solver.solve()

    # all assignments equally valid, so can change fractional assignment
    F = np.transpose(np.array([
        [0.4, 0.4, 0.4],
        [0.4, 0.4, 0.4],
        [0.2, 0.2, 0.2]
    ]))
    solver.fractional_assignment_matrix = F
    for _ in range(100):
        solver.sample_assignment()
        check_sampled_solution(solver)

def test_solution_optimal_no_limit():
    ''' Test that the correct optimal solution is found without probability limits '''
    S = np.transpose(np.array([
        [0.1, 0.4, 0.7],
        [0.3, 0.6, 0.5],
        [0.5, 0.8, 0.5]
    ]))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 1.0)

    solver = RandomizedSolver(
        [0,0,0],
        [2,2,2],
        [2,2,2],
        encoder(-S, M, Q)
    )
    solution = np.transpose(np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0]
    ]))
    solver.solve()

    assert np.all(solver.fractional_assignment_matrix == solution) and np.all(solver.flow_matrix == solution)
    assert solver.expected_cost == -3.2 and solver.cost == -3.2
    solver.sample_assignment() # should not change since assignment is deterministic
    assert np.all(solver.fractional_assignment_matrix == solution) and np.all(solver.flow_matrix == solution)
    assert solver.expected_cost == -3.2 and solver.cost == -3.2

def test_constraints():
    ''' Ensure constraint matrix is respected '''
    S = np.transpose(np.array([
        [1, 0.1, 0.5],
        [1, 1, 0.5],
        [0.3, 0.6, 0.5],
        [0.5, 0.8, 0.5]
    ]))
    M = np.transpose(np.array([
        [-1, 1, 0],
        [0, -1, 0],
        [0, 0, 1],
        [0, 0, 1]
    ]))
    Q = np.full(np.shape(S), 0.75)

    solver = RandomizedSolver(
        [0,0,0,0],
        [3,3,3,3],
        [2,2,2],
        encoder(-S, M, Q)
    )
    check_test_solution(solver)


def test_large():
    ''' Ensure things still work in a larger case '''
    p = 20
    r = 60
    S = np.random.random((p, r))
    M = np.zeros(np.shape(S))
    Q = np.full(np.shape(S), 0.5)
    solver = RandomizedSolver(
        [1] * r,
        [3] * r,
        [3] * p,
        encoder(-S, M, Q)
    )
    check_test_solution(solver, 100, 0.2)