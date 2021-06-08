'''
A paper-reviewer assignment solver that maximizes expected total affinity,
obeying limits on the marginal probabilities of each paper-reviewer assignment.

The assignment is found in two steps: (1) an LP is solved to find the optimal
"fractional assignment" (i.e., a marginal probability for each reviewer-paper
pair), and (2) the fractional assignment is sampled from. The sampling
procedure is implemented in C in the bvn_extension/ folder and accessed using
the CFFI library. This algorithm is detailed in Jecmen et al 2020.

Alternates are also selected probabilistically so that the probability limits
are maintained even if all alternates are used.
'''

from .simple_solver import SimpleSolver
from .core import SolverException
from .bvn_extension import run_bvn
from ortools.linear_solver import pywraplp
from cffi import FFI
import logging
import numpy as np
from itertools import product

class RandomizedSolver():
    def __init__(
            self,
            minimums,
            maximums,
            demands,
            encoder,
            allow_zero_score_assignments=False,
            logger=logging.getLogger(__name__)
        ):
        self.minimums = minimums
        self.maximums = maximums
        self.demands = demands
        self.cost_matrix = encoder.cost_matrix
        self.num_paps, self.num_revs = self.cost_matrix.shape
        self.allow_zero_score_assignments = allow_zero_score_assignments
        self.logger = logger

        if not self.cost_matrix.any():
            self.cost_matrix = np.random.rand(*encoder.cost_matrix.shape)

        self.constraint_matrix = encoder.constraint_matrix

        self.prob_limit_matrix = encoder.prob_limit_matrix

        if not self.allow_zero_score_assignments:
            bad_affinity_reviewers = np.where(np.all((self.cost_matrix * (self.constraint_matrix == 0)) == 0,
                                                     axis=0))[0]
            self.logger.debug("Setting minimum load for {} reviewers to 0 because "
                          "they do not have known affinity with any paper".format(len(bad_affinity_reviewers)))
            for rev_id in bad_affinity_reviewers:
                self.minimums[rev_id] = 0

        self.solved = False
        self.fractional_assignment_matrix = None
        self.expected_cost = None # expected cost of the fractional assignment
        self.flow_matrix = None
        self.cost = None # actual cost of the sampled assignment
        self.alternate_probability_matrix = None # marginal probability for each alternate
        self.opt_solved = False
        self.opt_cost = None # cost of the optimal deterministic assignment

        self.integer_fractional_assignment_matrix = None # actual solution to LP
        self.one = 10000000 # precision of fractional assignment

        self._check_inputs()
        self.fractional_assignment_solver = self.construct_solver(self.prob_limit_matrix)
        self.deterministic_assignment_solver = self.construct_solver(np.ones_like(self.prob_limit_matrix))


    def _check_inputs(self):
        '''Validate inputs (e.g. that matrix and array dimensions are correct)'''
        self.logger.debug('Checking graph inputs')

        for matrix in [self.cost_matrix, self.constraint_matrix, self.prob_limit_matrix]:
            if not isinstance(matrix, np.ndarray):
                raise SolverException(
                    'cost, constraint, and probability limit matrices must be of type numpy.ndarray')

        if (not np.shape(self.cost_matrix) == (self.num_paps, self.num_revs) or
                not np.shape(self.constraint_matrix) == (self.num_paps, self.num_revs) or
                not np.shape(self.prob_limit_matrix) == (self.num_paps, self.num_revs)):
            raise SolverException(
                'cost {}, constraint {}, and probability limit {} matrices must be the same shape'.format(
                    np.shape(self.cost_matrix), np.shape(self.constraint_matrix), np.shape(self.prob_limit_matrix)))

        if not len(self.minimums) == self.num_revs or not len(self.maximums) == self.num_revs:
            raise SolverException(
                'minimums ({}) and maximums ({}) must be same length as number of reviewers ({})'.format(
                    len(self.minimums), len(self.maximums), self.num_revs))

        if not len(self.demands) == self.num_paps:
            raise SolverException(
                'self.demands array must be same length ({}) as number of papers ({})'.format(
                    len(self.demands), self.num_paps))

        # check that probabilities are legal
        if np.any(np.logical_or(self.prob_limit_matrix > 1, self.prob_limit_matrix < 0)):
            raise SolverException('Some probability limits are not in [0, 1]')

        self.logger.debug('Finished checking graph inputs')


    def _validate_input_range(self):
        '''Validate if demand is in the range of min supply and max supply'''
        self.logger.debug('Checking if demand is in range')

        min_supply = sum(self.minimums)
        max_supply = sum(self.maximums)
        demand = sum(self.demands)

        self.logger.debug('Total demand is ({}), min review supply is ({}), and max review supply is ({})'.format(demand, min_supply, max_supply))

        if demand > max_supply or demand < min_supply:
            raise SolverException('Total demand ({}) is out of range when min review supply is ({}) and max review supply is ({})'.format(demand, min_supply, max_supply))

        self.logger.debug('Finished checking if demand is in range')

    def construct_solver(self, limit_matrix):
        ''' LP is solved with all probabilities scaled up by self.one. Solution is assumed to be integral. '''
        self.logger.debug('construct_solver')
        lp_solver = pywraplp.Solver.CreateSolver('GLOP')

        F = [[None for j in range(self.num_revs)] for i in range(self.num_paps)]
        for i, j in product(range(self.num_paps), range(self.num_revs)):
            constraint = self.constraint_matrix[i, j]
            limit = int(self.one * limit_matrix[i, j])
            if constraint == 0 and (self.allow_zero_score_assignments or self.cost_matrix[i, j] != 0):
                # no conflict
                F[i][j] = lp_solver.NumVar(0, limit, "F[{}][{}]".format(i, j))
            elif constraint == 1:
                # assign to paper as much as possible given limits
                F[i][j] = lp_solver.NumVar(limit, limit, "F[{}][{}]".format(i, j))
            else:
                # conflict
                F[i][j] = lp_solver.NumVar(0, 0, "F[{}][{}]".format(i, j))

        for i in range(self.num_paps):
            c = lp_solver.Constraint(int(self.one*self.demands[i]), int(self.one*self.demands[i]))
            for j in range(self.num_revs):
                c.SetCoefficient(F[i][j], 1)

        for j in range(self.num_revs):
            c = lp_solver.Constraint(int(self.one*self.minimums[j]), int(self.one*self.maximums[j]))
            for i in range(self.num_paps):
                c.SetCoefficient(F[i][j], 1)

        objective = lp_solver.Objective()
        for i, j in product(range(self.num_paps), range(self.num_revs)):
            objective.SetCoefficient(F[i][j], self.cost_matrix[i, j])
        objective.SetMinimization()

        self.logger.debug('Finished construct_solver')
        return lp_solver


    def solve(self):
        self.logger.debug('solve')

        self._validate_input_range()

        assert hasattr(self, 'fractional_assignment_solver'), \
            'Solver not constructed. Run self.construct_solver(self.probability_limit_matrix) first.'

        self.logger.debug('start fractional_assignment_solver')

        self.expected_cost = 0
        status = self.fractional_assignment_solver.Solve()
        if status == self.fractional_assignment_solver.OPTIMAL:
            self.solved = True
            self.expected_cost = self.fractional_assignment_solver.Objective().Value() / self.one

            self.integer_fractional_assignment_matrix = np.zeros((self.num_paps, self.num_revs), dtype=np.intc)
            for i, j in product(range(self.num_paps), range(self.num_revs)):
                actual_value = self.fractional_assignment_solver.LookupVariable("F[{}][{}]".format(i, j)).solution_value()
                assert np.round(actual_value) - actual_value < 1e-5, 'LP solution should be integral'
                self.integer_fractional_assignment_matrix[i, j] = np.round(actual_value) # assumes that round does not ruin paper load integrality

            assert np.all(np.sum(self.integer_fractional_assignment_matrix, axis=1) % self.one == 0), \
                'Paper loads should be "integral"'

            self.fractional_assignment_matrix = self.integer_fractional_assignment_matrix / self.one
        else:
            self.logger.debug("Solver status: {}".format(status))
            self.solved = False
            return

        self.logger.debug('start deterministic_assignment_solver')

        self.opt_cost = 0
        status = self.deterministic_assignment_solver.Solve()
        if status == self.deterministic_assignment_solver.OPTIMAL:
            self.opt_solved = True
            self.opt_cost = self.deterministic_assignment_solver.Objective().Value() / self.one
        else:
            self.logger.debug("Deterministic solver status: {}".format(status))
            self.opt_solved = False

        self.logger.debug('set alternate_probability_matrix')
        # set alternate probability to guarantee that
        # P[(p, r) assigned OR alternate] <= self.prob_limit_matrix[p, r]
        # by setting P[alternate] = (prob_limit - P[assign]) / (1 - P[assign])
        self.alternate_probability_matrix = np.divide(self.prob_limit_matrix - self.fractional_assignment_matrix,
                1 - self.fractional_assignment_matrix,
                out=(np.zeros_like(self.prob_limit_matrix)), # if fractional assignment is 1, alternate probability is 0
                where=(self.fractional_assignment_matrix != 1))

        self.sample_assignment()
        self.logger.debug('Finished solve')

        return self.flow_matrix


    def sample_assignment(self):
        ''' Sample a deterministic assignment from the fractional assignment '''
        self.logger.debug('sample_assignment')

        assert self.solved, \
            'Solver not solved. Run self.solve() before sampling.'

        # construct CFFI interface to the sampling extension in C
        ffi = FFI()
        F = self.integer_fractional_assignment_matrix.flatten()
        Fbuf = ffi.new("int[]", self.num_paps * self.num_revs)
        for i in range(F.size):
            Fbuf[i] = F[i]
        Sbuf = ffi.new("int[]", self.num_revs)
        for i in range(self.num_revs):
            Sbuf[i] = 1

        run_bvn(Fbuf, Sbuf, self.num_paps, self.num_revs, self.one)

        self.flow_matrix = np.zeros((self.num_paps, self.num_revs))
        for i in range(F.size):
            coords = np.unravel_index(i, (self.num_paps, self.num_revs))
            self.flow_matrix[coords] = Fbuf[i]

        self.cost = np.sum(self.flow_matrix * self.cost_matrix)

        # check that sampled assignment is valid
        pap_loads = np.sum(self.flow_matrix, axis=1)
        rev_loads = np.sum(self.flow_matrix, axis=0)
        if not (np.all(pap_loads == np.array(self.demands)) and
                np.all(np.logical_and(rev_loads <= np.array(self.maximums), rev_loads >= np.array(self.minimums)))):
            raise SolverException('Sampled assignment is invalid')

        self.logger.debug('Finished sample_assignment')



    def get_alternates(self, num_alternates):
        ''' Sample alternates in order to respect probability guarantees '''
        self.logger.debug('get_alternates')

        assert self.solved, \
            'Solver not solved. Run self.solve() before sampling.'

        rng = np.random.default_rng()

        alternates_by_index = {}
        for i in range(self.num_paps):
            unassigned = []
            for j in range(self.num_revs):
                # only allow j as an alternate with limited probability
                if self.flow_matrix[i, j] == 0 and rng.random() < self.alternate_probability_matrix[i, j]:
                    unassigned.append((self.cost_matrix[i, j], j))
            unassigned.sort()
            alternates_by_index[i] = [entry[1] for entry in unassigned[:num_alternates]]
        self.logger.debug('Finished get_alternates')
        return alternates_by_index

    def get_fraction_of_opt(self):
        '''
        Return the fraction of the optimal score achieved by the randomized assignment (in expectation).
        This is sensible as long as costs = score * -scale.
        '''
        self.logger.debug('get_fraction_of_opt')

        assert self.solved and self.opt_solved, \
            'Fractional and optimal solvers not solved. Run self.solve() before sampling.'

        return self.expected_cost / self.opt_cost if self.opt_cost != 0 else 1
