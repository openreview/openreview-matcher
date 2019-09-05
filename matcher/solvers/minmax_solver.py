'''
A paper-reviewer assignment solver that ensures a minimum paper load per reviewer, if possible.

First calls an iteration of SimpleSolver with minimum reviewer loads,
then calls a second iteration, accounting for the results from the first iteration.

Arguments are the same as SimpleSolver,
except that the "num_reviews" argument is replaced by "minimums" and "maximums".

    "minimums" & "maximums":
    lists of length #reviewers. Each item in the lists is an
        integer representing the minimum/maximum number of reviews a reviewer
        should be assigned.

'''
import numpy as np
import logging
from .simple_solver import SimpleSolver

class MinMaxSolver:
    '''Implements a min/max assignment graph solver.'''
    def __init__(
            self,
            minimums,
            maximums,
            demands,
            cost_matrix,
            constraint_matrix,
            logger=logging.getLogger(__name__)
        ):

        self.minimums = minimums
        self.maximums = maximums
        self.demands = demands
        self.cost_matrix = cost_matrix
        self.constraint_matrix = constraint_matrix

        self.solved = False
        self.flow_matrix = None
        self.optimal_cost = None
        self.cost = None

        self.logger = logger

    def solve(self):
        '''Computes combined solution of two SimpleSolvers'''

        minimum_solver = SimpleSolver(
            self.minimums,
            self.demands,
            self.cost_matrix,
            self.constraint_matrix,
            logger=self.logger,
            strict=False
        ) # strict=False prevents errors from being thrown for supply/demand mismatch


        minimum_result = minimum_solver.solve()

        adjusted_constraints = self.constraint_matrix - minimum_solver.flow_matrix
        adjusted_maximums = self.maximums - np.sum(minimum_solver.flow_matrix, axis=0)
        adjusted_demands = self.demands - np.sum(minimum_solver.flow_matrix, axis=1)

        maximum_solver = SimpleSolver(
            adjusted_maximums,
            adjusted_demands,
            self.cost_matrix,
            adjusted_constraints,
            logger=self.logger)

        maximum_result = maximum_solver.solve()

        self.solved = True
        self.optimal_cost = minimum_solver.min_cost_flow.OptimalCost() + \
            maximum_solver.min_cost_flow.OptimalCost()

        self.flow_matrix = minimum_result + maximum_result
        self.cost = np.sum(self.flow_matrix * self.cost_matrix)

        return self.flow_matrix
