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
from .core import SolverException
import time

class MinMaxSolver:
    '''Implements a min/max assignment graph solver.'''
    def __init__(
            self,
            minimums,
            maximums,
            demands,
            encoder,
            logger=logging.getLogger(__name__)
        ):

        self.minimums = minimums
        self.maximums = maximums
        self.demands = demands
        self.cost_matrix = encoder.cost_matrix

        if not self.cost_matrix.any():
            self.cost_matrix = np.random.rand(*encoder.cost_matrix.shape)

        self.constraint_matrix = encoder.constraint_matrix

        self.solved = False
        self.flow_matrix = None
        self.optimal_cost = None
        self.cost = None
        self.logger = logger

    def _validate_input_range(self):
        '''Validate if demand is in the range of min supply and max supply'''
        self.logger.debug('Checking if demand is in range')

        num_papers = np.size(self.cost_matrix, axis=0)
        num_reviewers = np.size(self.cost_matrix, axis=1)

        min_supply = sum(self.minimums)
        max_supply = sum(self.maximums)
        demand = sum(self.demands)

        self.logger.debug('total demand is ({}), min review supply is ({}), and max review supply is ({}), '.format(demand, min_supply, max_supply))

        if demand > max_supply or demand < min_supply:
            raise SolverException('total demand ({}) is out of range when min review supply is ({}) and max review supply is ({}), '.format(demand, min_supply, max_supply))

        self.logger.debug('Finished checking graph inputs')

    def solve(self):
        '''Computes combined solution of two SimpleSolvers'''
        self._validate_input_range()

        start_time = time.time()
        self.logger.debug('Min Solver started at={}'.format(start_time))
        minimum_solver = SimpleSolver(
            self.minimums,
            self.demands,
            self.cost_matrix,
            self.constraint_matrix,
            logger=self.logger,
            strict=False
        ) # strict=False prevents errors from being thrown for supply/demand mismatch
        minimum_result = minimum_solver.solve()
        stop_time = time.time()
        self.logger.debug('Min Solver finished at {} and took {} seconds'.format(stop_time, stop_time - start_time))

        adjusted_constraints = self.constraint_matrix - minimum_solver.flow_matrix
        adjusted_maximums = self.maximums - np.sum(minimum_solver.flow_matrix, axis=0)
        adjusted_demands = self.demands - np.sum(minimum_solver.flow_matrix, axis=1)

        start_time = time.time()
        self.logger.debug('Max Solver started at={}'.format(start_time))
        maximum_solver = SimpleSolver(
            adjusted_maximums,
            adjusted_demands,
            self.cost_matrix,
            adjusted_constraints,
            logger=self.logger)

        maximum_result = maximum_solver.solve()
        stop_time = time.time()
        self.logger.debug('Max Solver finished at {} and took {} seconds'.format(stop_time, stop_time - start_time))

        self.solved = minimum_solver.solved and maximum_solver.solved

        self.optimal_cost = minimum_solver.min_cost_flow.OptimalCost() + \
            maximum_solver.min_cost_flow.OptimalCost()

        self.flow_matrix = minimum_result + maximum_result
        self.cost = np.sum(self.flow_matrix * self.cost_matrix)

        return self.flow_matrix
