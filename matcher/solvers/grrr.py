from collections import defaultdict
from ortools.graph import pywrapgraph
import numpy as np
import random
import uuid
import time
from .core import SolverException
import logging


class GRRR(object):
    """
    Assign reviewers using the Greedy Reviewer Round-Robin algorithm
    from I Will Have Order! Optimizing Orders for Fair Reviewer Assignment
    (https://arxiv.org/abs/2108.02126). This algorithm outputs an approximately
    optimal assignment that satisfies the envy-free up to 1 item (EF1) criterion.

    Reviewer Round-Robin (RRR) puts papers in a random order, then allows each
    paper to choose its favorite reviewer one-by-one in order. Some constraints
    apply to the selection process - most importantly, no paper can choose a
    reviewer that would cause an EF1 violation. Greedy RRR (GRRR) approximately
    finds the order of papers that produces the highest overall welfare when input
    to RRR.
    """

    def __init__(self, minimums, maximums, demands, encoder, allow_zero_score_assignments=False, solution=None,
                 logger=logging.getLogger(__name__)):
        """
        Initialize a GRRR matcher

        :param minimums: a list of integers specifying the minimum number of papers for each reviewer.
        :param maximums: a list of integers specifying the maximum number of papers for each reviewer.
        :param demands: a list of integers specifying the number of reviews required per paper.
        :param encoder: an Encoder class object used to get affinity and constraint matrices.
        :param allow_zero_score_assignments: bool to allow pairs with zero affinity in the solution.
            unknown matching scores default to 0. set to True to allow zero (unknown) affinity in solution.
        :param solution: a matrix of assignments (same shape as encoder.affinity_matrix)

        :return: initialized makespan matcher.
        """
        self.logger = logger
        self.logger.debug('Init GRRR')
        self.constraint_matrix = encoder.constraint_matrix.transpose()
        affinity_matrix = encoder.aggregate_score_matrix.transpose()

        """
        The number of papers to consider in each step of _select_ordering().
        Higher sample_size can improve objective score at the cost of increased runtime.
        """
        self.sample_size = 10

        self.maximums = maximums
        self.minimums = minimums
        self.demands = demands

        # make sure that all weights are positive:
        self.affinity_matrix = affinity_matrix.copy()
        if not self.affinity_matrix.any():
            self.affinity_matrix = np.random.rand(*affinity_matrix.shape)

        self.best_revs = np.argsort(-1 * self.affinity_matrix, axis=0)

        self.orig_affinities = self.affinity_matrix.copy()

        self.num_reviewers = np.size(self.affinity_matrix, axis=0)
        self.num_papers = np.size(self.affinity_matrix, axis=1)

        self.id = uuid.uuid4()
        self.solution = solution if solution else np.zeros((self.num_reviewers, self.num_papers))
        assert (self.affinity_matrix.shape == self.solution.shape)
        self.max_affinities = np.max(self.affinity_matrix)

        self.solved = False
        self.logger.debug('End Init GRRR')

    def _validate_input_range(self):
        """Validate if demand is in the range of min supply and max supply,
        and forbids currently unsupported settings."""
        self.logger.debug('Checking if demand is in range')

        min_supply = sum(self.minimums)
        max_supply = sum(self.maximums)
        demand = sum(self.demands)

        self.logger.debug(
            'Total demand is ({}), min review supply is ({}), and max review supply is ({})'.format(demand, min_supply,
                                                                                                    max_supply))

        if np.any(self.minimums):
            raise SolverException(
                'GRRR does not currently support minimum values for number of papers per reviewer')

        if np.min(self.demands) < np.max(self.demands):
            raise SolverException(
                'GRRR does not currently support different demands for each paper')

        if demand > max_supply or demand < min_supply:
            raise SolverException('Total demand ({}) is out of range when max review '
                                  'supply is ({})'.format(demand, min_supply, max_supply))

        self.logger.debug('Finished checking graph inputs')

    def objective_val(self):
        """Get the objective value of the RAP."""
        return np.sum(self.sol_as_mat() * self.orig_affinities)

    def sol_as_mat(self):
        if self.solved:
            return self.solution
        else:
            raise SolverException(
                'You must have solved for an ordering and run round-robin before calling this function')

    def is_safe_choice(self, r, p, order_idx_map, matrix_alloc, papers_who_tried_revs, round_num, first_reviewer):
        """Ensure that we can assign reviewer r to paper p without breaking envy-freeness up to 1 item.

        If we are assigning the first reviewer to each paper, then EF1 cannot be broken. Otherwise,
        we must check any paper which has taken or tried to take r in the past. If that paper comes before
        p in the round-robin ordering, then make sure it values its own reviewers over p's current reviewers and r.
        If that paper comes after p, make sure it values its own reviewers over p's current reviewers, minus p's
        first-choice reviewer, plus r.

        See the paper I Will Have Order! Optimizing Orders for Reviewer Assignment for more details.

        Args:
            r - (int) the id of the reviewer we want to add
            p - (int) the id of the paper to which we are adding r
            order_idx_map - (dict) maps papers to their index in the round-robin order
            matrix_alloc - (2d numpy array) the current allocation
            papers_who_tried_revs - (dict) maps each reviewer to a list of papers that have tried to select it
            round_num - (int) the round of round-robin
            first_reviewer - (dict) maps each paper to the reviewer it chose in round 0

        Returns:
            True if r can be assigned to p without violating EF1, False otherwise.
        """
        if round_num == 0 or not len(papers_who_tried_revs[r]):
            return True
        p_idx = order_idx_map[p]

        # Construct the allocations we'll use for comparison
        p_alloc_orig = matrix_alloc[:, p]
        p_alloc_proposed = p_alloc_orig.copy()
        p_alloc_proposed[r] = 1
        p_alloc_proposed_reduced = p_alloc_proposed.copy()
        p_alloc_proposed_reduced[first_reviewer[p]] = 0

        for q in papers_who_tried_revs[r]:
            if q != p:
                # Check that they will not envy a if we add r to a.
                _p = p_alloc_proposed if (order_idx_map[q] < p_idx) else p_alloc_proposed_reduced
                q_value_for_p_proposed = np.sum(_p * self.affinity_matrix[:, q])

                q_value_for_q = np.sum(matrix_alloc[:, q] * self.affinity_matrix[:, q])
                if q_value_for_p_proposed > q_value_for_q \
                        and not np.isclose(q_value_for_p_proposed, q_value_for_q):
                    return False
        return True

    def safe_rr(self, ordering):
        """Compute round-robin assignment with the papers in this ordering.

        Papers select their favorite remaining reviewer in each round,
        subject to constraints - papers cannot pick a reviewer which would
        cause another paper to envy them up to more than 1 reviewer, and they
        cannot pick a reviewer which is forbidden by the predefined constraint_matrix.

        Args:
            ordering - (list) ordered list of a subset of papers for round-robin

        Returns:
            A 2d numpy array with an EF1 partial allocation to the papers in ordering.
            The array has the same shape as self.affinity_matrix, with a 1 in the i, j
            entry when reviewer i is assigned to paper j (and 0 otherwise).
        """
        matrix_alloc = np.zeros(self.affinity_matrix.shape, dtype=np.bool)
        maximums_copy = self.maximums.copy()

        papers_who_tried_revs = defaultdict(list)
        first_reviewer = {}

        order_idx_map = {p: idx for idx, p in enumerate(ordering)}

        for round_num in range(self.demands[ordering[0]]):
            for a in ordering:
                new_assn = False
                for r in self.best_revs[:, a]:
                    if maximums_copy[r] > 0 \
                            and r not in np.where(matrix_alloc[:, a])[0] \
                            and self.constraint_matrix[r, a] == 0:
                        if self.is_safe_choice(r, a, order_idx_map, matrix_alloc,
                                               papers_who_tried_revs, round_num, first_reviewer):
                            maximums_copy[r] -= 1
                            matrix_alloc[r, a] = 1
                            if round_num == 0:
                                first_reviewer[a] = r
                            papers_who_tried_revs[r].append(a)
                            new_assn = True
                            break
                        else:
                            papers_who_tried_revs[r].append(a)
                if not new_assn:
                    raise SolverException(
                        'GRRR was unable to find an EF1 allocation satisfying all papers\' demands')
        return matrix_alloc

    def _compute_usw(self, ordering):
        """Compute the utilitarian social welfare (USW) for the assignment produced
        by running round-robin assignment with the papers in this ordering.

        Args:
            ordering - (list) ordered list of a subset of papers for round-robin

        Returns:
            USW, as a float.
        """
        matrix_alloc = self.safe_rr(ordering)
        return np.sum(matrix_alloc * self.affinity_matrix)

    def _select_ordering(self):
        """Greedily select a paper ordering for round-robin.

        At each step, we consider adding some subset of the remaining papers to the
        end of the current ordering. We add the paper which results in the largest
        USW of all papers in the subset.

        Args:
            None

        Returns:
            A list of all papers in the greedily-selected order.
        """
        m, n = self.affinity_matrix.shape

        available_agents = set(range(n))
        ordering = []

        curr_usw = 0
        mg_upper_bound = np.max(self.demands) * np.max(self.affinity_matrix)

        while len(ordering) < n:
            next_agent = None
            best_usw = -np.inf

            sample_size = min(self.sample_size, len(available_agents))
            sorted_agents = sorted(random.sample(available_agents, sample_size))
            for a in sorted_agents:
                usw = self._compute_usw(ordering + [a])
                if usw > best_usw:
                    best_usw = usw
                    next_agent = a
                if best_usw - curr_usw == mg_upper_bound:
                    break

            curr_usw = best_usw
            ordering.append(next_agent)
            available_agents.remove(next_agent)
        return ordering

    def solve(self):
        """Find an approximately optimal order and run round-robin assignment.

        Args:
            None

        Returns:
            The solution as a matrix.
        """

        self._validate_input_range()

        ordering = self._select_ordering()
        self.solution = self.safe_rr(ordering)

        self.solved = True
        return self.sol_as_mat().transpose()
