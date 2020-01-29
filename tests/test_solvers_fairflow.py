# TODO: This is a leftover module from the days of David. Clean this up / make it readable!
from collections import namedtuple
import pytest
import numpy as np
from matcher.solvers import SolverException, FairFlow

encoder = namedtuple('Encoder', ['aggregate_score_matrix', 'constraint_matrix'])

def test_solvers_fairflow_random():
    '''When costs are all zero, compute random assignments'''
    aggregate_score_matrix_A = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    solver_A = FairFlow(
        [1,1,1,1],
        [2,2,2,2],
        [1,1,2],
        encoder(aggregate_score_matrix_A, constraint_matrix)
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3,4)

    aggregate_score_matrix_B = np.transpose(np.array([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ]))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_B))
    solver_B = FairFlow(
        [1,1,1,1],
        [2,2,2,2],
        [1,1,2],
        encoder(aggregate_score_matrix_B, constraint_matrix)
    )
    res_B = solver_B.solve()
    assert res_B.shape == (3,4)

    # ensure that the affinity matrices are random
    # (i.e. overwhelmingly likely to be different)
    assert not np.array_equal(solver_A.affinity_matrix, solver_B.affinity_matrix)

def test_solver_impossible_constraints():
    '''
    Test to ensure that the FairFlow solver's 'solved' attribute is correctly set
    when no solution is possible due to constraints.
    '''

    # 20 papers, 5 reviewers
    num_papers = 20
    num_reviewers = 5
    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = -1 * np.ones((num_papers, num_reviewers)) # all pairs are constrained! should be impossible

    minimums = [5] * 5
    maximums = [20] * 5
    demands = [3] * 20

    solver = FairFlow(
        minimums,
        maximums,
        demands,
        encoder(aggregate_score_matrix, constraint_matrix)
    )

    with pytest.raises(SolverException):
        solution = solver.solve()

    assert not solver.solved

def test_solver_respects_constraints():
    '''
    Tests 5 papers, 4 reviewers. Reviewers review min: 1, max: 3 papers. Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 2,3
             2: cannot review papers 2,3
             3: cannot review papers 0, 1
    All scores set to 1 so that any match that does not violate constraints is optimal
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

    solver = FairFlow(
        [1,1,1,1],
        [3,3,3,3],
        [2,2,2,2,2],
        encoder(aggregate_score_matrix, constraint_matrix)
    )

    res = solver.solve()
    assert res.shape == (5, 4)
    assert solver.solved
    # make sure result does not violate constraints (i.e. no flow at i,j if there is a -1 constraint at i,j
    nrows, ncols = res.shape
    for i in range(nrows):
        for j in range(ncols):
            assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)

def test_solver_respect_constraints_2():
    '''
    Tests 5 papers, 4 reviewers. Reviewers review min: 1, max: 3 papers. Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 0,3
             2: cannot review papers 3,4
             3: cannot review papers 1,2
    Scores set such that a lowest-cost solution can be found along all reviewer-paper arcs with cost = -10 and no others.
    Purpose:  Finds the lowest cost solution in combination with honoring constraints (i.e. ignores lower-cost paths that are constrained to be ommitted)
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

    solver = FairFlow(
        [1,1,1,1],
        [3,3,3,3],
        [2,2,2,2,2],
        encoder(aggregate_score_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (5, 4)
    assert solver.solved
    # make sure result does not violate constraints (i.e. no flow at i,j if there is a -1 constraint at i,j
    nrows, ncols = res.shape
    for i in range(nrows):
        for j in range(ncols):
            assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)

def test_solver_respect_minimums():
    '''
    Tests 6 papers, 6 reviewers.   Reviewers review min: 2, max: 3 papers.   Each paper needs 2 reviews.
    All scores set to 1 so that any match that does not violate constraints is optimal
    Purpose:  Honors minimums == 2 for all reviewers
    '''
    aggregate_score_matrix = np.array([
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

    solver = FairFlow(
        [2,2,2,2,2,2],
        [3,3,3,3,3,3],
        [2,2,2,2,2,2],
        encoder(aggregate_score_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (6,6)
    assert solver.solved

    # make sure every reviewer is reviewing 2 papers
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews == 2

def test_solver_respect_minimums_2():
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
    aggregate_score_matrix = np.transpose(np.array([
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
    solver = FairFlow(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1

def test_solver_respect_minimums_3():
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
    aggregate_score_matrix = np.transpose(np.array([
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
    solver = FairFlow(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1

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
    aggregate_score_matrix = np.transpose(np.array([
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
    solver = FairFlow(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
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
    aggregate_score_matrix = np.transpose(np.array([
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
    solver = FairFlow(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix)
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape
    for rix in range(nrows):
        reviewer_count_reviews = 0
        for pix in range(ncols):
            if res[rix,pix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1
