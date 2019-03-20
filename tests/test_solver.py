import numpy as np
from matcher.assignment_graph.AssignmentGraph import AssignmentGraph, GraphBuilder


class TestSolver:
    ''' Unit tests that check the correctness of teh SimpleGraphBuilder Solver'''

    @classmethod
    def setup_class(cls):
        cls.silent = True

    def test_solver1 (self):
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

    def test_solver2 (self):
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

    def test_solver3 (self):
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