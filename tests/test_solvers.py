# TODO: This is a leftover module from the days of David. Clean this up / make it readable!
from collections import namedtuple
import pytest
import numpy as np
from matcher.solvers import MinMaxSolver

encoder = namedtuple('Encoder', ['cost_matrix', 'constraint_matrix'])

def check_solution(solver, expected_cost):
    assert solver.optimal_cost == solver.cost, "Minimum cost solution is not the sum of the flows * unit cost in result matrix"
    assert solver.cost == expected_cost,  "Lowest cost solution should have cost = {}".format(expected_cost)

def test_solvers_minmax_random():
    '''When costs are all zero, compute random assignments'''
    cost_matrix_A = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(cost_matrix_A))
    solver_A = MinMaxSolver(
        [1,1,1,1],
        [2,2,2,2],
        [1,1,2],
        encoder(cost_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3,4)

    cost_matrix_B = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(cost_matrix_B))
    solver_B = MinMaxSolver(
        [1,1,1,1],
        [2,2,2,2],
        [1,1,2],
        encoder(cost_matrix_B, constraint_matrix)
    )
    res_B = solver_B.solve()
    assert res_B.shape == (3,4)
    print(res_A)
    print(res_B)
    assert not np.array_equal(solver_A.cost_matrix, solver_B.cost_matrix)

def test_solver_finds_lowest_cost_soln():
    '''
    4 reviewers 3 papers.   Papers 0,1 need 1 review; Paper 2 needs 2 reviews.  Reviewers can do max of 2 reviews
    Setup so that lowest cost solution should be
    Reviewer 0 reviews paper 0
             1 reviews paper 1
             2 reviews paper 2
             3 reviews paper 2
    Purpose:  Finds the lowest cost solution
    '''
    cost_matrix = np.transpose(np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
        [2, 2, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(cost_matrix))
    solver = MinMaxSolver(
        [1,1,1,1],
        [2,2,2,2],
        [1,1,2],
        encoder(cost_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3,4)

    expected_cost = 0
    check_solution(solver, expected_cost)

def test_solver_respects_constraints():
    '''
    Tests 5 papers, 4 reviewers.   Reviewers review min: 1, max: 3 papers.   Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 2,3
             2: cannot review papers 2,3
             3: cannot review papers 0, 1
    All scores set to 1 so that any match that does not violate constraints is optimal
    Purpose:  Honors constraints in its solution
    '''
    cost_matrix = np.transpose(np.array([
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1]]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0, 0, 0],
        [0, 0, -1, -1, 0],
        [0, 0, -1, -1, 0],
        [-1, -1, 0, 0, 0]]))

    solver = MinMaxSolver(
        [1,1,1,1],
        [3,3,3,3],
        [2,2,2,2,2],
        encoder(cost_matrix, constraint_matrix)
    )

    res = solver.solve()
    assert res.shape == (5, 4)
    # make sure result does not violate constraints (i.e. no flow at i,j if there is a -1 constraint at i,j
    nrows, ncols = res.shape
    for i in range(nrows):
        for j in range(ncols):
            assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)

    check_solution(solver, solver.optimal_cost)

def test_solver_find_lowest_cost_and_respect_constraints():
    '''
    Tests 5 papers, 4 reviewers.   Reviewers review min: 1, max: 3 papers.   Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 0,3
             2: cannot review papers 3,4
             3: cannot review papers 1,2
    Scores set such that a lowest-cost solution can be found along all reviewer-paper arcs with cost = -10 and no others.
    Purpose:  Finds the lowest cost solution in combination with honoring constraints (i.e. ignores lower-cost paths that are constrained to be ommitted)
    '''
    cost_matrix = np.transpose(np.array([
        [-10, 1, 1, -10, -10],
        [-100, -10, -10, -100, 1],
        [1, -10, -10, -100, -100],
        [-10, -100, -100, -10, -10]]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0, 0, 0],
        [-1, 0, 0, -1, 0],
        [0, 0 , 0, -1, -1],
        [0, -1,-1, 0, 0]]))

    solver = MinMaxSolver(
        [1,1,1,1],
        [3,3,3,3],
        [2,2,2,2,2],
        encoder(cost_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (5, 4)
    # make sure result does not violate constraints (i.e. no flow at i,j if there is a -1 constraint at i,j
    # make sure the score at i,j = -10 if there is flow there.
    nrows, ncols = res.shape
    for i in range(nrows):
        for j in range(ncols):
            assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)
            assert not (res[i,j] > 0 and cost_matrix[i,j] > -10), "Solution contains an arc that is not part of an lowest-cost solution"
    check_solution(solver,solver.optimal_cost)

def test_solver4():
    '''
    Tests 6 papers, 6 reviewers.   Reviewers review min: 2, max: 3 papers.   Each paper needs 2 reviews.
    All scores set to 1 so that any match that does not violate constraints is optimal
    Purpose:  Honors minimums == 2 for all reviewers
    '''
    cost_matrix = np.array([
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1]])
    constraint_matrix = np.array([
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0]])

    solver = MinMaxSolver(
        [2,2,2,2,2,2],
        [3,3,3,3,3,3],
        [2,2,2,2,2,2],
        encoder(cost_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (6,6)
    # make sure every reviewer is reviewing 2 papers
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews == 2
    check_solution(solver,solver.optimal_cost)

def test_solver5():
    '''
    Tests 3 papers, 4 reviewers.   Reviewers review min: 1, max: 3 papers.   Each paper needs 3 reviews.
    Reviewer 4 has very high cost.  Other reviewers have 0 cost.
    Purpose:  Make sure all reviewers get at least their minimum
    '''
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 1
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    cost_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [2000, 2000, 2000]]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]]))


    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = MinMaxSolver(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(cost_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1
    # TestSolver.silent = False
    check_solution(solver,solver.optimal_cost)

def test_solver6():
    '''
    Tests 3 papers, 4 reviewers.   Reviewers review min: 2, max: 3 papers.   Each paper needs 3 reviews.
    Reviewer 4 has very high cost.  Other reviewers have 0 cost.
    Purpose:  Make sure all reviewers get at least their minimum
    '''
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 2
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    cost_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [2000, 2000, 2000]]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]]))

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = MinMaxSolver(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(cost_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1
    # TestSolver.silent = False
    check_solution(solver,solver.optimal_cost)

def test_solver_respects_one_minimum():
    '''
    Tests 3 papers, 4 reviewers.   Reviewers review min: 1, max: 3 papers.   Each paper needs 3 reviews.
    Reviewer 4 has very high cost.  Other reviewers have 0 cost.
    Purpose:  Make sure all reviewers (including reviewer 4) get at least their minimum
    '''
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 1
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    cost_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [2000, 2000, 2000]]))

    constraint_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]]))

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = MinMaxSolver(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(cost_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1

def test_solver_respects_two_minimum():
    '''
    Tests 3 papers, 4 reviewers.   Reviewers review min: 2, max: 3 papers.   Each paper needs 3 reviews.
    Reviewer 4 has very high cost.  Other reviewers have 0 cost.
    Purpose:  Make sure all reviewers (including reviewer 4) get at least their minimum
    '''
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 2
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    cost_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [2000, 2000, 2000]]))
    constraint_matrix = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]]))

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = MinMaxSolver(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(cost_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1

