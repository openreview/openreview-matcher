from collections import namedtuple
import pytest
import numpy as np
from matcher.solvers import SolverException, FairSequence
from conftest import assert_arrays

encoder = namedtuple(
    "Encoder", ["aggregate_score_matrix", "constraint_matrix"]
)


def test_solvers_fairsequence_random():
    """When affinities are all zero, compute random assignments"""
    aggregate_score_matrix_A = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    )
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2, 2, 2]
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [2, 2, 2, 2],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    assert solver_A.solved

    aggregate_score_matrix_B = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    )
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_B))
    solver_B = FairSequence(
        [0, 0, 0, 0],
        [2, 2, 2, 2],
        demands,
        encoder(aggregate_score_matrix_B, constraint_matrix),
    )
    res_B = solver_B.solve()
    assert res_B.shape == (3, 4)
    assert solver_B.solved

    # ensure that the affinity matrices are random
    # (i.e. overwhelmingly likely to be different)
    assert not np.array_equal(
        solver_A.affinity_matrix, solver_B.affinity_matrix
    )
    result_A = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result_A, demands)
    result_B = [assignments for assignments in np.sum(res_B, axis=1)]
    assert_arrays(result_B, demands)


def test_solvers_fairsequence_custom_supply():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: [3,2,3,2] papers respectively.
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
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [3, 2, 3, 2],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
        allow_zero_score_assignments=True,
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result_demands = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result_demands, demands)
    result_supply = [assignments for assignments in np.sum(res_A, axis=0)]
    for (i, j) in zip(result_supply, [3, 2, 3, 2]):
        assert i <= j


def test_solvers_fairsequence_custom_demands():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 1, max: 2 papers.
    Papers need [2,1,3] reviews.
    No constraints.
    Purpose: Assert that papers demands are matched.
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
    solver_A = FairSequence(
        [1, 1, 1, 1],
        [2, 2, 2, 2],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result, demands)


def test_solvers_fairsequence_custom_demand_and_supply():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: [2,2,3,2] papers.
    The 3 Papers need 2,1,3 reviews.
    No constraints.
    Purpose: Assert that custom demand and supply are matched.
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
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [2, 2, 3, 2],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result, demands)
    result_supply = [assignments for assignments in np.sum(res_A, axis=0)]
    for (i, j) in zip(result_supply, [2, 2, 3, 2]):
        assert i <= j


def test_solvers_fairsequence_custom_demands_paper_with_0_demand():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: 2 papers.
    The 3 Papers need 2,1,0 reviews.
    No constraints.
    Purpose: Assert that reviewers demanding 0 papers get 0 assignments.
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
    demands = [2, 1, 0]
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [2, 2, 2, 2],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result, demands)


def test_solver_fairsequence_no_0_score_assignment():
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

    solver = FairSequence(
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


def test_solver_fairsequence_impossible_constraints():
    """
    Test to ensure that the FairSequence solver's 'solved' attribute is correctly set
    when no solution is possible due to constraints.
    """

    # 20 papers, 5 reviewers
    num_papers = 20
    num_reviewers = 5
    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = -1 * np.ones(
        (num_papers, num_reviewers)
    )  # all pairs are constrained! should be impossible

    minimums = [0] * 5
    maximums = [20] * 5
    demands = [3] * 20

    solver = FairSequence(
        minimums,
        maximums,
        demands,
        encoder(aggregate_score_matrix, constraint_matrix),
    )

    with pytest.raises(SolverException):
        solver.solve()

    assert not solver.solved


def test_solver_fairsequence_respects_constraints():
    """
    Tests 5 papers, 4 reviewers.
    Reviewers review min: 0, max: 5 papers.
    Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 2,3
             2: cannot review papers 2,3
             3: cannot review papers 0,1
    All scores set to 1 so that any match that does not violate constraints is optimal.
    Purpose:  Honors constraints in its solution
    """
    aggregate_score_matrix = np.transpose(
        np.array(
            [
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
            ]
        )
    )
    constraint_matrix = np.transpose(
        np.array(
            [
                [0, 0, 0, 0, 0],
                [0, 0, -1, -1, 0],
                [0, 0, -1, -1, 0],
                [-1, -1, 0, 0, 0],
            ]
        )
    )

    solver = FairSequence(
        [0, 0, 0, 0],
        [5, 5, 5, 5],
        [2, 2, 2, 2, 2],
        encoder(aggregate_score_matrix, constraint_matrix),
    )

    res = solver.solve()
    assert res.shape == (5, 4)
    assert solver.solved
    # make sure result does not violate constraints
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for i in range(nrows):
        for j in range(ncols):
            assert not (
                constraint_matrix[i, j] == -1 and res[i, j] > 0
            ), "Solution violates constraint at [{},{}]".format(i, j)


def test_solver_fairsequence_respect_constraints_2():
    """
    Tests 5 papers, 4 reviewers.
    Reviewers review min: 0, max: 3 papers.
    Each paper needs 2 reviews.
    Constrained such that:
    Reviewer 0: available for all papers
             1: cannot review papers 0,3
             2: cannot review papers 3,4
             3: cannot review papers 1,2
    Purpose: Honors constraints in its solution
    """
    aggregate_score_matrix = np.transpose(
        np.array(
            [
                [-10, 1, 1, -10, -10],
                [-100, -10, -10, -100, 1],
                [1, -10, -10, -100, -100],
                [-10, -100, -100, -10, -10],
            ]
        )
    )
    constraint_matrix = np.transpose(
        np.array(
            [
                [0, 0, 0, 0, 0],
                [-1, 0, 0, -1, 0],
                [0, 0, 0, -1, -1],
                [0, -1, -1, 0, 0],
            ]
        )
    )

    solver = FairSequence(
        [0, 0, 0, 0],
        [3, 3, 3, 3],
        [2, 2, 2, 2, 2],
        encoder(aggregate_score_matrix, constraint_matrix),
    )
    res = solver.solve()
    assert res.shape == (5, 4)
    assert solver.solved
    # make sure result does not violate constraints
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for i in range(nrows):
        for j in range(ncols):
            assert not (
                constraint_matrix[i, j] == -1 and res[i, j] > 0
            ), "Solution violates constraint at [{},{}]".format(i, j)


def wef1(allocation, affinities, demands):
    """
    Not a test, but is a criterion for tests.

    Checks if the allocation is weighted envy-free up to 1 item (WEF1).
    For all papers i and j with demands w_i and w_j and assignments a_i and a_j,
    we require that v_i(a_i)/w_i >= v_i(a_j - g)/w_j for some g. Note that this
    is equivalent to standard envy-free up to 1 item (EF1) when w_i = w_j for all i,j.

    Args:
        allocation - (2d numpy array) assignment of reviewers to papers
        affinities - (2d numpy array) affinities between papers and reviewers

    Returns:
        True if the allocation satisfies the WEF1 criterion, otherwise False.
    """
    n = allocation.shape[0]
    for i in range(n):
        # i's value for self
        i_value_i = np.sum(allocation[i, :] * affinities[i, :]) / demands[i]
        i_value_others = (
            np.sum(affinities[i, :] * allocation, axis=1) / demands
        )
        possible_envy = i_value_others > i_value_i
        possible_envy = np.where(possible_envy)[0]
        for j in possible_envy:
            # i's lowest value for j, minus a good
            i_value_j_up_to_1 = np.sum(
                allocation[j, :] * affinities[i, :]
            ) - np.max(allocation[j, :] * affinities[i, :])
            i_value_j_up_to_1 /= demands[j]
            if i_value_j_up_to_1 > i_value_i and not np.isclose(
                i_value_j_up_to_1, i_value_i
            ):
                return False
    return True


def test_solver_fairsequence_envy_free_up_to_one_item():
    """
    Tests 10 papers, 15 reviewers, for 10 random affinity matrices.
    Reviewers review min: 0, max: 3 papers.
    Each paper needs 3 reviews.
    No constraints.
    Purpose: Ensure that the FairSequence solver returns allocations that are envy-free up to 1 item
        when paper demands are uniform.
    """
    num_papers = 10
    num_reviewers = 15

    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix))

    minimums = [0] * num_reviewers
    maximums = [3] * num_reviewers
    demands = [3] * num_papers

    for _ in range(10):
        solver = FairSequence(
            minimums,
            maximums,
            demands,
            encoder(aggregate_score_matrix, constraint_matrix),
        )
        res = solver.solve()

        assert res.shape == (10, 15)
        assert solver.solved
        assert wef1(res, solver.affinity_matrix.transpose(), demands)


def test_solver_fairsequence_envy_free_up_to_one_item_constrained():
    """
    Tests 10 papers, 15 reviewers, for 10 random affinity matrices.
    Reviewers review min: 0, max: 3 papers.
    Each paper needs 3 reviews.
    Constraints chosen at random, with a 10% chance of any given constraint.
    Purpose: Ensure that the FairSequence solver returns allocations that are envy-free up to 1 item and satisfy constraints
        when paper demands are uniform.
    """
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
            -1 * np.ones(shape),
        )

        solver = FairSequence(
            minimums,
            maximums,
            demands,
            encoder(aggregate_score_matrix, constraint_matrix),
        )
        res = solver.solve()

        assert res.shape == (10, 15)
        assert solver.solved
        assert wef1(res, solver.affinity_matrix.transpose(), demands)

        nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
        for i in range(nrows):
            for j in range(ncols):
                assert not (
                    constraint_matrix[i, j] == -1 and res[i, j] > 0
                ), "Solution violates constraint at [{},{}]".format(i, j)


def test_solver_fairsequence_weighted_envy_free_up_to_one_item():
    """
    Tests 10 papers, 15 reviewers, for 10 random affinity matrices.
    Reviewers review min: 1, max: 6 papers.
    Each paper needs between 1 and 6 reviews.
    No constraints.
    Purpose: Ensure that the FairSequence solver returns allocations that are weighted envy-free up to 1 item.
    """
    num_papers = 10
    num_reviewers = 15

    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix))

    minimums = [1] * num_reviewers
    maximums = [6] * num_reviewers

    for _ in range(10):
        demands = np.random.randint(1, 7, size=num_papers)

        solver = FairSequence(
            minimums,
            maximums,
            demands,
            encoder(aggregate_score_matrix, constraint_matrix),
        )
        res = solver.solve()

        assert res.shape == (10, 15)
        assert solver.solved
        assert wef1(res, solver.affinity_matrix.transpose(), demands)


def test_solver_fairsequence_weighted_envy_free_up_to_one_item_constrained():
    """
    Tests 10 papers, 20 reviewers, for 10 random affinity matrices.
    Reviewers review min: 1, max: 6 papers.
    Each paper needs between 1 and 6 reviews.
    Constraints chosen at random, with a 10% chance of any given constraint.
    Purpose: Ensure that the FairSequence solver returns allocations that are weighted
     envy-free up to 1 item and satisfy constraints.
    """
    num_papers = 10
    num_reviewers = 20

    aggregate_score_matrix = np.zeros((num_papers, num_reviewers))
    shape = np.shape(aggregate_score_matrix)

    minimums = [0] * num_reviewers
    maximums = [6] * num_reviewers

    for _ in range(10):
        demands = np.random.randint(1, 7, size=num_papers)

        constraint_matrix = np.where(
            np.random.rand(shape[0], shape[1]) > 0.1,
            np.zeros(shape),
            -1 * np.ones(shape),
        )

        solver = FairSequence(
            minimums,
            maximums,
            demands,
            encoder(aggregate_score_matrix, constraint_matrix),
        )
        res = solver.solve()

        assert res.shape == (10, 20)
        assert solver.solved
        assert wef1(res, solver.affinity_matrix.transpose(), demands)

        nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
        for i in range(nrows):
            for j in range(ncols):
                assert not (
                    constraint_matrix[i, j] == -1 and res[i, j] > 0
                ), "Solution violates constraint at [{},{}]".format(i, j)


def test_solver_fairsequence_respect_minimums():
    """
    Tests 6 papers, 6 reviewers.
    Reviewers review min: 2, max: 3 papers.
    Each paper needs 2 reviews.
    All scores set to 1 so that any match that does not violate constraints is optimal.
    Purpose:  Honors minimums == 2 for all reviewers
    """
    aggregate_score_matrix = np.array(
        [
            [1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1],
        ]
    )
    constraint_matrix = np.array(
        [
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
        ]
    )

    solver = FairSequence(
        [2, 2, 2, 2, 2, 2],
        [3, 3, 3, 3, 3, 3],
        [2, 2, 2, 2, 2, 2],
        encoder(aggregate_score_matrix, constraint_matrix),
    )
    res = solver.solve()
    assert res.shape == (6, 6)
    assert solver.solved

    # make sure every reviewer is reviewing 2 papers
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for rix in range(ncols):
        reviewer_count_reviews = 0
        for pix in range(nrows):
            if res[pix, rix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews == 2


def test_solver_fairsequence_respect_minimums_2():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 1, max: 3 papers.
    Each paper needs 3 reviews.
    Reviewer 4 has very high affinity.
    Other reviewers have 0 affinity.
    Purpose:  Make sure all reviewers get at least their minimum
    """
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 1
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    aggregate_score_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [2000, 2000, 2000]])
    )
    constraint_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    )

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = FairSequence(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix),
        allow_zero_score_assignments=True,
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for rix in range(ncols):
        reviewer_count_reviews = 0
        for pix in range(nrows):
            if res[pix, rix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1


def test_solver_fairsequence_respect_minimums_3():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 2, max: 3 papers.
    Each paper needs 3 reviews.
    Reviewer 4 has very high affinity.
    Other reviewers have 0 affinity.
    Purpose:  Make sure all reviewers get at least their minimum
    """
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 2
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    aggregate_score_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [2000, 2000, 2000]])
    )
    constraint_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    )

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = FairSequence(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix),
        allow_zero_score_assignments=True,
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for rix in range(ncols):
        reviewer_count_reviews = 0
        for pix in range(nrows):
            if res[pix, rix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 2


def test_solver_fairsequence_respects_one_minimum():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 1, max: 3 papers.
    Each paper needs 3 reviews.
    Reviewer 4 has very high affinity.
    Other reviewers have 0 affinity.
    Purpose:  Make sure all reviewers (including reviewer 4) get at least their minimum
    """
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 1
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    aggregate_score_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [2000, 2000, 2000]])
    )

    constraint_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    )

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = FairSequence(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix),
        allow_zero_score_assignments=True,
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for rix in range(ncols):
        reviewer_count_reviews = 0
        for pix in range(nrows):
            if res[pix, rix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 1


def test_solver_fairsequence_respects_two_minimum():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 2, max: 3 papers.
    Each paper needs 3 reviews.
    Reviewer 4 has very high affinity.
    Other reviewers have 0 affinity.
    Purpose:  Make sure all reviewers (including reviewer 4) get at least their minimum
    """
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 2
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    aggregate_score_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [2000, 2000, 2000]])
    )
    constraint_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    )

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = FairSequence(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix),
        allow_zero_score_assignments=True,
    )
    res = solver.solve()
    assert res.shape == (3, 4)
    assert solver.solved
    # make sure every reviewer has at least 1 paper
    nrows, ncols = res.shape if len(res.shape) == 2 else (0, 0)
    for rix in range(ncols):
        reviewer_count_reviews = 0
        for pix in range(nrows):
            if res[pix, rix] != 0:
                reviewer_count_reviews += 1
        assert reviewer_count_reviews >= 2


def test_solver_fairsequence_avoid_zero_scores_get_no_solution():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 2, max: 3 papers.
    Each paper needs 3 reviews.
    Most reviewers have 0 affinity.
    Purpose:  Make sure the matcher fails when mostly 0 scores and allow_zero_score_assignments=False
    """
    num_papers = 3
    num_reviewers = 4
    min_papers_per_reviewer = 2
    max_papers_per_reviewer = 3
    paper_revs_reqd = 3
    aggregate_score_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 1, 0]])
    )
    constraint_matrix = np.transpose(
        np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    )

    rev_mins = [min_papers_per_reviewer] * num_reviewers
    rev_maxs = [max_papers_per_reviewer] * num_reviewers
    papers_reqd = [paper_revs_reqd] * num_papers
    solver = FairSequence(
        rev_mins,
        rev_maxs,
        papers_reqd,
        encoder(aggregate_score_matrix, constraint_matrix),
        allow_zero_score_assignments=False,
    )

    with pytest.raises(
        SolverException,
        match=r"Solver could not find a solution. Adjust your parameters.",
    ):
        res = solver.solve()


def test_solvers_fairsequence_make_trades():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: [2,1,1,3] papers.
    The 3 Papers need 2,1,3 reviews.
    No constraints.
    Purpose: The original WEF1 picking sequence should fail.
    Then we ensure that by trading around reviewers,
    we can still return an allocation.
    """
    aggregate_score_matrix_A = np.transpose(
        np.array(
            [
                [0.2, 0.1, 0.4],
                [0.5, 0.2, 0.4],
                [0.7, 0.9, 0.1],
                [0.2, 0.9, 0.6],
            ]
        )
    )
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2, 1, 3]
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [2, 1, 1, 3],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result, demands)
    expected_solution = np.array(
        [
            [1, 1, 0, 0],
            [0, 0, 0, 1],
            [1, 0, 1, 1],
        ]
    )
    assert np.all(res_A == expected_solution)
    assert solver_A.alpha == 1.0


def test_solvers_fairsequence_make_trades_alpha_blocking():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: [2,1,1,3] papers.
    The 3 Papers need 2,1,3 reviews.
    No constraints.
    Purpose: The original WEF1 picking sequence should fail.
    We try to see if we can trade around reviewers that papers consider
    equivalent up to a factor of alpha and still return an allocation.
    When we set alpha too high, we should fail to find a sequence of trades.
    """
    aggregate_score_matrix_A = np.transpose(
        np.array(
            [
                [0.2, 0.1, 0.4],
                [0.5, 0.2, 0.4],
                [0.7, 0.9, 0.1],
                [0.2, 0.8, 0.6],
            ]
        )
    )
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2, 1, 3]
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [2, 1, 1, 3],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    solver_A.fixed_alpha = True
    solver_A.alpha = (8 / 9) + 0.001

    with pytest.raises(
        SolverException,
        match=r"Solver could not find a solution. Adjust your parameters.",
    ):
        res = solver_A.solve()


def test_solvers_fairsequence_make_trades_alpha_blocking_2():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: [2,1,1,3] papers.
    The 3 Papers need 2,1,3 reviews.
    No constraints.
    Purpose: The original WEF1 picking sequence should fail.
    We try to see if we can trade around reviewers that papers consider
    equivalent up to a factor of alpha and still return an allocation.
    When we set alpha just low enough, we find the right sequence of trades.
    """
    aggregate_score_matrix_A = np.transpose(
        np.array(
            [
                [0.2, 0.1, 0.4],
                [0.5, 0.2, 0.4],
                [0.7, 0.9, 0.1],
                [0.2, 0.8, 0.6],
            ]
        )
    )
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2, 1, 3]
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [2, 1, 1, 3],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    solver_A.fixed_alpha = True
    solver_A.alpha = (8 / 9) - 0.001
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result, demands)
    expected_solution = np.array(
        [
            [1, 1, 0, 0],
            [0, 0, 0, 1],
            [1, 0, 1, 1],
        ]
    )
    assert np.all(res_A == expected_solution)


def test_solvers_fairsequence_make_trades_alpha_blocking_3():
    """
    Tests 3 papers, 4 reviewers.
    Reviewers review min: 0, max: [2,1,1,3] papers.
    The 3 Papers need 2,1,3 reviews.
    No constraints.
    Purpose: The original WEF1 picking sequence should fail.
    We try to see if we can trade around reviewers that papers consider
    equivalent up to a factor of alpha and still return an allocation.
    The algorithm tries alpha = 1.0, 0.75, 0.5, 0.25, and 0.0, in that
    order. So we should succeed when alpha is the highest possible out of
    those options (0.5 for this example).
    """
    aggregate_score_matrix_A = np.transpose(
        np.array(
            [
                [0.3, 0.1, 0.4],
                [0.5, 0.2, 0.4],
                [0.7, 0.9, 0.0],
                [0.3, 0.6, 0.6],
            ]
        )
    )
    constraint_matrix = np.zeros(np.shape(aggregate_score_matrix_A))
    demands = [2, 1, 3]
    solver_A = FairSequence(
        [0, 0, 0, 0],
        [2, 1, 1, 3],
        demands,
        encoder(aggregate_score_matrix_A, constraint_matrix),
    )
    res_A = solver_A.solve()
    assert res_A.shape == (3, 4)
    result = [assignments for assignments in np.sum(res_A, axis=1)]
    assert_arrays(result, demands)
    expected_solution = np.array(
        [
            [1, 0, 0, 1],
            [0, 0, 1, 0],
            [1, 1, 0, 1],
        ]
    )
    assert np.all(res_A == expected_solution)
    assert solver_A.alpha == 0.5
