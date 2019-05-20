import numpy as np
from matcher.assignment_graph.AssignmentGraph import AssignmentGraph, GraphBuilder


class TestSolver:
    ''' Unit tests that check the correctness of teh SimpleGraphBuilder Solver'''

    @classmethod
    def setup_class(cls):
        cls.silent = True

    def test_solver_finds_lowest_cost_soln (self):
        '''
        4 reviewers 3 papers.   Papers 0,1 need 1 review; Paper 2 needs 2 reviews.  Reviewers can do max of 2 reviews
        Setup so that lowest cost solution should be
        Reviewer 0 reviews paper 0
                 1 reviews paper 1
                 2 reviews paper 2
                 3 reviews paper 2
        Purpose:  Finds the lowest cost solution
        '''
        cost_matrix = np.array([
            [0, 1, 1],
            [1, 0, 1],
            [1, 1, 0],
            [2, 2, 0]
        ])
        constraint_matrix = np.zeros(np.shape(cost_matrix))
        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        solver = AssignmentGraph([1,1,1,1], [2,2,2,2], [1,1,2], cost_matrix, constraint_matrix, graph_builder)
        res = solver.solve()
        assert res.shape == (4,3)
        self.print_header()
        cost = 0
        for i in range(solver.min_cost_flow.NumArcs()):
            cost += solver.min_cost_flow.Flow(i) * solver.min_cost_flow.UnitCost(i)
            self.print_arc(solver.min_cost_flow, i)
        assert solver.min_cost_flow.OptimalCost() == cost, "Minimum cost solution is not the sum of the flows * unit cost in result matrix"
        assert cost == 0,  "Lowest cost solution should have cost = 0"

    def test_solver_respects_constraints (self):
        '''
        Tests 4 papers, 3 reviewers.   Reviewers review min: 1, max: 3 papers.   Each paper needs 2 reviews.
        Constrained such that:
        Reviewer 0: available for all papers
                 1: cannot review papers 2,3
                 2: cannot review papers 2,3
                 3: cannot review papers 0, 1
        All scores set to 1 so that any match that does not violate constraints is optimal
        Purpose:  Honors constraints in its solution
        '''
        cost_matrix = np.array([
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1]])
        constraint_matrix = np.array([
            [0, 0, 0, 0, 0],
            [0, 0, -1, -1, 0],
            [0, 0, -1, -1, 0],
            [-1, -1, 0, 0, 0]])
        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        solver = AssignmentGraph([1,1,1,1], [3,3,3,3], [2,2,2,2,2], cost_matrix, constraint_matrix, graph_builder)
        res = solver.solve()
        assert res.shape == (4,5)
        # make sure result does not violate constraints (i.e. no flow at i,j if there is a -1 constraint at i,j
        nrows, ncols = res.shape
        for i in range(nrows):
            for j in range(ncols):
                assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)
        self.print_header()
        cost = 0
        for i in range(solver.min_cost_flow.NumArcs()):
            cost += solver.min_cost_flow.Flow(i) * solver.min_cost_flow.UnitCost(i)
            self.print_arc(solver.min_cost_flow, i)

        assert solver.min_cost_flow.OptimalCost() == cost, "Minimum cost solution is not the sum of the flows * unit cost in result matrix"

    def test_solver_find_lowest_cost_and_respect_constraints (self):
        '''
        Tests 4 papers, 3 reviewers.   Reviewers review min: 1, max: 3 papers.   Each paper needs 2 reviews.
        Constrained such that:
        Reviewer 0: available for all papers
                 1: cannot review papers 0,3
                 2: cannot review papers 3,4
                 3: cannot review papers 1,2
        Scores set such that a lowest-cost solution can be found along all reviewer-paper arcs with cost = -10 and no others.
        Purpose:  Finds the lowest cost solution in combination with honoring constraints (i.e. ignores lower-cost paths that are constrained to be ommitted)
        '''
        cost_matrix = np.array([
            [-10, 1, 1, -10, -10],
            [-100, -10, -10, -100, 1],
            [1, -10, -10, -100, -100],
            [-10, -100, -100, -10, -10]])
        constraint_matrix = np.array([
            [0, 0, 0, 0, 0],
            [-1, 0, 0, -1, 0],
            [0, 0 , 0, -1, -1],
            [0, -1,-1, 0, 0]])
        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        solver = AssignmentGraph([1,1,1,1], [3,3,3,3], [2,2,2,2,2], cost_matrix, constraint_matrix, graph_builder)
        res = solver.solve()
        assert res.shape == (4,5)
        # make sure result does not violate constraints (i.e. no flow at i,j if there is a -1 constraint at i,j
        # make sure the score at i,j = -10 if there is flow there.
        nrows, ncols = res.shape
        for i in range(nrows):
            for j in range(ncols):
                assert not (constraint_matrix[i,j] == -1 and res[i,j] > 0), "Solution violates constraint at [{},{}]".format(i,j)
                assert not (res[i,j] > 0 and cost_matrix[i,j] > -10), "Solution contains an arc that is not part of an lowest-cost solution"
        self.print_header()
        cost = 0
        for i in range(solver.min_cost_flow.NumArcs()):
            cost += solver.min_cost_flow.Flow(i) * solver.min_cost_flow.UnitCost(i)
            self.print_arc(solver.min_cost_flow, i)

        assert solver.min_cost_flow.OptimalCost() == cost, "Minimum cost solution is not the sum of the flows * unit cost in result matrix"


    def test_solver_respects_one_minimum (self):
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
        cost_matrix = np.array([
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [2000, 2000, 2000]])
        constraint_matrix = np.array([
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]])

        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        rev_mins = [min_papers_per_reviewer] * num_reviewers
        rev_maxs = [max_papers_per_reviewer] * num_reviewers
        papers_reqd = [paper_revs_reqd] * num_papers
        solver = AssignmentGraph(rev_mins, rev_maxs, papers_reqd, cost_matrix, constraint_matrix, graph_builder)
        res = solver.solve()
        assert res.shape == (4,3)
        # make sure every reviewer has at least 1 paper
        nrows, ncols = res.shape
        for rix in range(nrows):
            reviewer_count_reviews = 0
            for pix in range(ncols):
                if res[rix,pix] != 0:
                    reviewer_count_reviews += 1
            assert reviewer_count_reviews >= 1
        # TestSolver.silent = False
        print("-----")
        print("Reviewer min: {}, max: {}".format(min_papers_per_reviewer, max_papers_per_reviewer))
        print("cost matrix")
        print(cost_matrix)
        print("solution matrix")
        print(res)

    def test_solver_respects_two_minimum (self):
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
        cost_matrix = np.array([
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [2000, 2000, 2000]])
        constraint_matrix = np.array([
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]])

        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        rev_mins = [min_papers_per_reviewer] * num_reviewers
        rev_maxs = [max_papers_per_reviewer] * num_reviewers
        papers_reqd = [paper_revs_reqd] * num_papers
        solver = AssignmentGraph(rev_mins, rev_maxs, papers_reqd, cost_matrix, constraint_matrix, graph_builder)
        res = solver.solve()
        assert res.shape == (4,3)
        # make sure every reviewer has at least 1 paper
        nrows, ncols = res.shape
        for rix in range(nrows):
            reviewer_count_reviews = 0
            for pix in range(ncols):
                if res[rix,pix] != 0:
                    reviewer_count_reviews += 1
            assert reviewer_count_reviews >= 1
        # TestSolver.silent = False
        print("-----")
        print("Reviewer min: {}, max: {}".format(min_papers_per_reviewer, max_papers_per_reviewer))
        print("cost matrix")
        print(cost_matrix)
        print("solution matrix")
        print(res)

    def test_solver_respects_minimums_icml (self):
        '''
        Based on ICML workshop which produces a match that has users either getting 4 or 6 papers with one user
        getting just 2.
        There are 44 papers, 27 reviewers. 3 users per paper and between 4 and 6 papers per user.
        All reviewers are 0 cost.
        Purpose:  Make sure all reviewers get between their min and max
        TODO Why do all reviewers get either the min or max?  None of them get a number in between!
        '''
        num_papers = 44
        num_reviewers = 27
        min_papers_per_reviewer = 4
        max_papers_per_reviewer = 6
        paper_revs_reqd = 3
        cost_matrix = np.zeros((num_reviewers, num_papers))
        constraint_matrix = np.zeros((num_reviewers, num_papers))

        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        rev_mins = [min_papers_per_reviewer] * num_reviewers
        rev_maxs = [max_papers_per_reviewer] * num_reviewers
        papers_reqd = [paper_revs_reqd] * num_papers
        solver = AssignmentGraph(rev_mins, rev_maxs, papers_reqd, cost_matrix, constraint_matrix, graph_builder)
        res = solver.solve()
        assert res.shape == (27,44)
        # make sure every reviewer has >= minimum number of papers
        # make sure every reviewer has <= maximum number of papers
        nrows, ncols = res.shape
        total = 0
        num4=0
        num6=0
        for rix in range(nrows):
            reviewer_count_reviews = 0
            for pix in range(ncols):
                if res[rix,pix] != 0:
                    reviewer_count_reviews += 1
            total += reviewer_count_reviews
            if reviewer_count_reviews == 4:
                num4 += 1
            else:
                num6 += 1
            print("Reviewer: {} has {} papers".format(rix, reviewer_count_reviews))
            assert reviewer_count_reviews >= min_papers_per_reviewer
            assert reviewer_count_reviews <= max_papers_per_reviewer
        assert total == num_papers * paper_revs_reqd
        assert total == num4*4 + num6*6
        print("Total reviews",total, "num 4", num4, "num 6", num6)
        # TestSolver.silent = False
        print("-----")
        print("Reviewer min: {}, max: {}".format(min_papers_per_reviewer, max_papers_per_reviewer))
        print("cost matrix")
        print(cost_matrix)
        print("solution matrix")
        print(res)

    def print_header  (self):
        if not self.silent:
            print('  Arc    Flow / Capacity  Cost')

    def print_arc(self, graph, i):
        if not self.silent:
            cost = graph.Flow(i) * graph.UnitCost(i)
            print('%1s -> %1s   %3s  / %3s       %3s' % (
                graph.Tail(i),
                graph.Head(i),
                graph.Flow(i),
                graph.Capacity(i),
                cost))