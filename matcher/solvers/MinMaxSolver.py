from ..assignment_graph import AssignmentGraph
import numpy as np

class MinMaxSolver:
    '''
    Implements a min-cost network flow graph for the worker-task assignment problem
        (see: https://developers.google.com/optimization/flow/mincostflow)

    minimums/maximums: lists of length #reviewers. Each item in the lists is an
        integer representing the minimum/maximum number of reviews a reviewer
        should be assigned.

    demands: a list of integers of length #papers representing the number of
        reviews the paper should be assigned.

    cost_matrix: an #reviewers by #papers numpy array representing the cost of
        each reviewer-paper combination.

    constraint_matrix: an #reviewers by #papers numpy array representing
        constraints on the match. Each cell can take a value of -1, 0, or 1:

        0: no constraint
        1: strongly favor this pair
       -1: strongly avoid this pair
    '''

    def __init__(
        self,
        minimums,
        maximums,
        demands,
        cost_matrix,
        constraint_matrix):

        self.minimums = minimums
        self.maximums = maximums
        self.demands = demands
        self.cost_matrix = cost_matrix
        self.constraint_matrix = constraint_matrix

        self.solved = False
        self.flow_matrix = None
        self.optimal_cost = None
        self.cost = None

    def solve(self):
        minimum_solver = AssignmentGraph(
            self.minimums,
            self.demands,
            self.cost_matrix,
            self.constraint_matrix,
            strict=False)

        minimum_result = minimum_solver.solve()

        adjusted_constraints = self.constraint_matrix - minimum_solver.flow_matrix
        adjusted_maximums = self.maximums - np.sum(minimum_solver.flow_matrix, axis=1)
        adjusted_demands = self.demands - np.sum(minimum_solver.flow_matrix, axis=0)

        maximum_solver = AssignmentGraph(
            adjusted_maximums,
            adjusted_demands,
            self.cost_matrix,
            adjusted_constraints)

        maximum_result = maximum_solver.solve()

        self.solved = True
        self.optimal_cost = minimum_solver.min_cost_flow.OptimalCost() + \
            maximum_solver.min_cost_flow.OptimalCost()

        self.flow_matrix = minimum_result + maximum_result
        self.cost = np.sum(self.flow_matrix * self.cost_matrix)

        return self.flow_matrix



