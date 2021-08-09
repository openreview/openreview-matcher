"""
A paper-reviewer assignment solver that ensures a minimum paper load per reviewer, if possible.

First calls an iteration of SimpleSolver with minimum reviewer loads,
then calls a second iteration, accounting for the results from the first iteration.

Arguments are the same as SimpleSolver,
except that the "num_reviews" argument is replaced by "minimums" and "maximums".

    "minimums" & "maximums":
    lists of length #reviewers. Each item in the lists is an
        integer representing the minimum/maximum number of reviews a reviewer
        should be assigned.

"""
import numpy as np
import logging
from .simple_solver import SimpleSolver
from .core import SolverException
import time


class MinMaxSolver:
    """Implements a min/max assignment graph solver."""

    def __init__(
        self,
        minimums,
        maximums,
        demands,
        encoder,
        allow_zero_score_assignments=False,
        logger=logging.getLogger(__name__),
        limit_matrix=None,
    ):

        self.minimums = minimums
        self.maximums = maximums
        self.demands = demands
        self.cost_matrix = encoder.cost_matrix
        self.allow_zero_score_assignments = allow_zero_score_assignments
        if limit_matrix is None:
            self.limit_matrix = np.ones(
                np.shape(self.cost_matrix), dtype=np.int64
            )
        else:
            self.limit_matrix = limit_matrix

        if not self.cost_matrix.any():
            self.cost_matrix = np.random.rand(*encoder.cost_matrix.shape)

        self.constraint_matrix = encoder.constraint_matrix

        if not self.allow_zero_score_assignments:
            # Find reviewers with no known cost edges (non-zero) after constraints are applied and remove their load_lb
            bad_affinity_reviewers = np.where(
                np.all(
                    (self.cost_matrix * (self.constraint_matrix == 0)) == 0,
                    axis=0,
                )
            )[0]
            logging.debug(
                "Setting minimum load for {} reviewers to 0 because "
                "they do not have known affinity with any paper".format(
                    len(bad_affinity_reviewers)
                )
            )
            for rev_id in bad_affinity_reviewers:
                self.minimums[rev_id] = 0

        self.solved = False
        self.flow_matrix = None
        self.optimal_cost = None
        self.cost = None
        self.logger = logger

    def _validate_input_range(self):
        """Validate if demand is in the range of min supply and max supply"""
        self.logger.debug("Checking if demand is in range")

        min_supply = sum(self.minimums)
        max_supply = sum(self.maximums)
        demand = sum(self.demands)

        self.logger.debug(
            "Total demand is ({}), min review supply is ({}), and max review supply is ({})".format(
                demand, min_supply, max_supply
            )
        )

        if demand > max_supply or demand < min_supply:
            raise SolverException(
                "Total demand ({}) is out of range when min review supply is ({}) and max review supply is ({})".format(
                    demand, min_supply, max_supply
                )
            )

        self.logger.debug("Finished checking graph inputs")

    def solve(self):
        """Computes combined solution of two SimpleSolvers"""
        self._validate_input_range()

        start_time = time.time()
        self.logger.debug("Min Solver started at={}".format(start_time))
        minimum_solver = SimpleSolver(
            self.minimums,
            self.demands,
            self.cost_matrix,
            self.constraint_matrix,
            allow_zero_score_assignments=self.allow_zero_score_assignments,
            logger=self.logger,
            strict=False,
            limit_matrix=self.limit_matrix,
        )  # strict=False prevents errors from being thrown for supply/demand mismatch
        minimum_result = minimum_solver.solve()
        stop_time = time.time()
        self.logger.debug(
            "Min Solver finished at {} and took {} seconds".format(
                stop_time, stop_time - start_time
            )
        )

        adjusted_constraints = self.constraint_matrix
        adjusted_limits = self.limit_matrix - minimum_solver.flow_matrix
        adjusted_maximums = self.maximums - np.sum(
            minimum_solver.flow_matrix, axis=0
        )
        adjusted_demands = self.demands - np.sum(
            minimum_solver.flow_matrix, axis=1
        )

        start_time = time.time()
        self.logger.debug("Max Solver started at={}".format(start_time))
        maximum_solver = SimpleSolver(
            adjusted_maximums,
            adjusted_demands,
            self.cost_matrix,
            adjusted_constraints,
            allow_zero_score_assignments=self.allow_zero_score_assignments,
            logger=self.logger,
            limit_matrix=adjusted_limits,
        )

        maximum_result = maximum_solver.solve()
        stop_time = time.time()
        self.logger.debug(
            "Max Solver finished at {} and took {} seconds".format(
                stop_time, stop_time - start_time
            )
        )

        self.solved = minimum_solver.solved and maximum_solver.solved

        self.optimal_cost = (
            minimum_solver.min_cost_flow.OptimalCost()
            + maximum_solver.min_cost_flow.OptimalCost()
        )

        self.flow_matrix = minimum_result + maximum_result
        self.cost = np.sum(self.flow_matrix * self.cost_matrix)

        return self.flow_matrix
