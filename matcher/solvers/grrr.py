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
    Assign reviewers using a modified version of the Greedy Reviewer Round-Robin algorithm
    from I Will Have Order! Optimizing Orders for Fair Reviewer Assignment
    (https://arxiv.org/abs/2108.02126). This algorithm outputs an approximately
    optimal assignment that satisfies the weighted envy-free up to 1 item (WEF1) criterion.

    Reviewer Round-Robin (RRR) attempts to create an allocation of reviewers that is fair
    according to the weighted envy-free up to 1 item (WEF1) criterion. Papers pick reviewers
    one-by-one, with priority given to the papers with the lowest ratio of allocation size to demand.
    By default, ties in priority are resolved in a randomly selected, fixed order.
    If a sample_size greater than 1 is specified, the algorithm will perform a greedy search for an
    optimal tie-breaking order (using the specified number of samples at each step). Some constraints
    apply to the selection process - most importantly, no paper can choose a
    reviewer that would cause a WEF1 violation. If this procedure fails to discover a WEF1 allocation,
    we try the picking sequence again, allowing WEF1 violations during the process. 
    """

    def __init__(self, minimums, maximums, demands, encoder, allow_zero_score_assignments=False, solution=None,
                 sample_size=1, logger=logging.getLogger(__name__)):
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
        self.allow_zero_score_assignments = allow_zero_score_assignments
        self.logger.debug('Init GRRR')
        self.constraint_matrix = encoder.constraint_matrix.transpose()
        affinity_matrix = encoder.aggregate_score_matrix.transpose()


        # The number of papers to consider in each step of _select_ordering().
        # Higher sample_size can improve objective score at the cost of increased runtime.
        self.sample_size = sample_size

        self.maximums = np.array(maximums)
        self.minimums = np.array(minimums)
        self.demands = np.array(demands)

        self.affinity_matrix = affinity_matrix.copy()
        if not self.affinity_matrix.any():
            self.affinity_matrix = np.random.rand(*affinity_matrix.shape)

        self.best_revs = np.argsort(-1 * self.affinity_matrix, axis=0)

        self.orig_affinities = self.affinity_matrix.copy()

        self.num_reviewers = np.size(self.affinity_matrix, axis=0)
        self.num_papers = np.size(self.affinity_matrix, axis=1)

        if not self.allow_zero_score_assignments:
            # Find reviewers with no non-zero affinity edges after constraints are applied and remove their load_lb
            bad_affinity_reviewers = np.where(
                np.all(
                    (self.affinity_matrix * (self.constraint_matrix == 0))
                    == 0,
                    axis=1,
                )
            )[0]
            logging.debug(
                "Setting minimum load for {} reviewers to 0 "
                "because they do not have known affinity with any paper".format(
                    len(bad_affinity_reviewers)
                )
            )
            for rev_id in bad_affinity_reviewers:
                self.minimums[rev_id] = 0

        self.id = uuid.uuid4()
        self.solution = solution if solution else np.zeros((self.num_reviewers, self.num_papers))
        assert (self.affinity_matrix.shape == self.solution.shape)

        self.solved = False
        self.logger.debug('End Init GRRR')

    def _validate_input_range(self):
        """Validate if demand is in the range of min supply and max supply,
        and forbids currently unsupported settings."""
        self.logger.debug('Checking if demand is in range')

        min_supply = np.sum(self.minimums)
        max_supply = np.sum(self.maximums)
        demand = np.sum(self.demands)

        self.logger.debug(
            'Total demand is ({}), min review supply is ({}), and max review supply is ({})'.format(demand, min_supply,
                                                                                                    max_supply))

        if demand > max_supply or demand < min_supply:
            raise SolverException('Total demand ({}) is out of range when min review supply is ({}) '
                                  'and max review supply is ({})'.format(demand, min_supply, max_supply))

        self.logger.debug('Finished checking input ranges')

    def objective_val(self):
        """Get the objective value of the RAP."""
        return np.sum(self.sol_as_mat() * self.orig_affinities)

    def sol_as_mat(self):
        if self.solved:
            return self.solution
        else:
            raise SolverException(
                'You must have executed solve() before calling this function')

    def is_safe_choice(self, r, p, order_idx_map, matrix_alloc, papers_who_tried_revs, first_reviewer):
        """Ensure that we can assign reviewer r to paper p without breaking weighted envy-freeness up to 1 item.

        If we are assigning the first reviewer to each paper, then WEF1 cannot be broken. Otherwise,
        we must check any paper which has taken or tried to take r in the past. If that paper comes before
        p in the round-robin ordering, then make sure it values its own reviewers over p's current reviewers and r.
        If that paper comes after p, make sure it values its own reviewers over p's current reviewers, minus p's
        first-choice reviewer, plus r. Every value comparison is weighted, to ensure Weighted EF1.

        See the papers I Will Have Order! Optimizing Orders for Reviewer Assignment by Payan and Zick 2021
        for more on envy-free reviewer assignment and
        Weighted Envy-Freeness in Indivisible Item Allocation by Chakraborty et al. 2020 for more on WEF1.

        Args:
            r - (int) the id of the reviewer we want to add
            p - (int) the id of the paper to which we are adding r
            order_idx_map - (dict) maps papers to their index in the round-robin order
            matrix_alloc - (2d numpy array) the current allocation
            papers_who_tried_revs - (dict) maps each reviewer to a list of papers that have tried to select it
            first_reviewer - (dict) maps each paper to the reviewer it chose in round 0

        Returns:
            True if r can be assigned to p without violating WEF1, False otherwise.
        """
        if p not in first_reviewer or not len(papers_who_tried_revs[r]):
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

                q_value_for_p_proposed = np.sum(_p * self.affinity_matrix[:, q]) / self.demands[p]
                q_value_for_q = np.sum(matrix_alloc[:, q] * self.affinity_matrix[:, q]) / self.demands[q]

                if q_value_for_q < q_value_for_p_proposed \
                        and not np.isclose(q_value_for_p_proposed, q_value_for_q):
                    return False
        return True

    def _restrict_if_necessary(self, reviewers_remaining, matrix_alloc, paper_list):
        """Determine the number of papers we can still assign to each reviewer

        If we have exactly enough remaining reviewer slots to satisfy reviewer
        minima, then we set the remaining reviewers to be exactly the reviewers
        that need their minima satisfied.

        Args:
            reviewers_remaining - (1d numpy array) maximum number of papers each reviewer can
                still be assigned
            matrix_alloc - (2d numpy array) the assignment of reviewers to papers (papers are the rows)
            paper_list - (list) a subset of papers that we are currently assigning to

        Returns:
            New reviewers_remaining - either the same as the input if we have enough papers to satisfy
            reviewer minima, or the exact assignments required to meet minima otherwise.
        """
        remaining_demand = np.sum(self.demands[paper_list]) - np.sum(matrix_alloc)
        required_for_min = self.minimums - np.sum(matrix_alloc, axis=1)
        required_for_min[required_for_min < 0] = 0
        return required_for_min if np.sum(required_for_min) >= remaining_demand else reviewers_remaining

    def _select_next_paper(self, matrix_alloc, order_idx_map):
        """Select the next paper to pick a reviewer

        Each paper i has priority t_i/w_i, where t_i is the number of reviewers already
        assigned to paper i, and w_i is the total demand of paper i. The
        paper with lowest priority is chosen, with ties broken by the given ordering.
        For rationale, please see:
        Weighted Envy-Freeness in Indivisible Item Allocation by Chakraborty et al. 2020.

        Args:
            matrix_alloc - (2d numpy array) the assignment of reviewers to papers (papers are the columns)
            order_idx_map - (dict) a map from (some of) the papers to their positions in an order,
                used to break ties in priority

        Returns:
            The index of the next paper to pick a reviewer
        """
        priorities = np.sum(matrix_alloc, axis=0) / self.demands
        return sorted(order_idx_map.items(), key=lambda x: (priorities[x[0]], x[1]))[0][0]

    def rr(self, ordering):
        """Compute round-robin assignment with the papers in this ordering.

        Papers select their favorite remaining reviewer in each round,
        subject only to constraints in the constraint_matrix.

        Args:
            ordering - (list) ordered list of a subset of papers for round-robin

        Returns:
            A 2d numpy array with a partial allocation to the papers in ordering.
            The array has the same shape as self.affinity_matrix, with a 1 in the i, j
            entry when reviewer i is assigned to paper j (and 0 otherwise).
        """
        matrix_alloc = np.zeros(self.affinity_matrix.shape, dtype=bool)
        maximums_copy = self.maximums.copy()

        order_idx_map = {p: idx for idx, p in enumerate(ordering)}

        while np.sum(matrix_alloc) < np.sum(self.demands[ordering]):
            maximums_copy = self._restrict_if_necessary(maximums_copy, matrix_alloc, ordering)
            a = self._select_next_paper(matrix_alloc, order_idx_map)

            new_assn = False
            for r in self.best_revs[:, a]:
                if maximums_copy[r] > 0 \
                        and r not in np.where(matrix_alloc[:, a])[0] \
                        and self.constraint_matrix[r, a] == 0 \
                        and (self.allow_zero_score_assignments or self.affinity_matrix[r, a]):

                    maximums_copy[r] -= 1
                    matrix_alloc[r, a] = 1
                    new_assn = True
                    break
            if not new_assn:
                return None
        return matrix_alloc

    def safe_rr(self, ordering):
        """Compute round-robin assignment with the papers in this ordering, with safeguards to ensure WEF1.

        Papers select their favorite remaining reviewer in each round,
        subject to constraints - papers cannot pick a reviewer which would
        cause another paper to envy them up to more than 1 reviewer, and they
        cannot pick a reviewer which is forbidden by the predefined constraint_matrix.

        Args:
            ordering - (list) ordered list of a subset of papers for round-robin

        Returns:
            A 2d numpy array with a WEF1 partial allocation to the papers in ordering.
            The array has the same shape as self.affinity_matrix, with a 1 in the i, j
            entry when reviewer i is assigned to paper j (and 0 otherwise).
        """
        matrix_alloc = np.zeros(self.affinity_matrix.shape, dtype=bool)
        maximums_copy = self.maximums.copy()

        papers_who_tried_revs = defaultdict(list)
        first_reviewer = {}

        order_idx_map = {p: idx for idx, p in enumerate(ordering)}

        while np.sum(matrix_alloc) < np.sum(self.demands[ordering]):
            maximums_copy = self._restrict_if_necessary(maximums_copy, matrix_alloc, ordering)
            a = self._select_next_paper(matrix_alloc, order_idx_map)

            new_assn = False
            for r in self.best_revs[:, a]:
                if maximums_copy[r] > 0 \
                        and r not in np.where(matrix_alloc[:, a])[0] \
                        and self.constraint_matrix[r, a] == 0 \
                        and (self.allow_zero_score_assignments or self.affinity_matrix[r, a]):
                    if self.is_safe_choice(r, a, order_idx_map, matrix_alloc, papers_who_tried_revs, first_reviewer):
                        maximums_copy[r] -= 1
                        matrix_alloc[r, a] = 1
                        if a not in first_reviewer:
                            first_reviewer[a] = r
                        papers_who_tried_revs[r].append(a)
                        new_assn = True
                        break
                    else:
                        papers_who_tried_revs[r].append(a)
            if not new_assn:
                return None
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
        return np.sum(matrix_alloc * self.affinity_matrix) if matrix_alloc is not None else None

    def _select_ordering(self):
        """Greedily select a paper ordering for round-robin.

        At each step, we consider adding some subset of the remaining papers to the
        end of the current ordering. We add the paper which results in the largest
        USW of all papers in the subset. If order selection fails, we default to a random ordering.

        Args:
            None

        Returns:
            A list of all papers in the greedily-selected order.
        """
        m, n = self.affinity_matrix.shape

        available_agents = set(range(n))
        ordering = []

        curr_usw = 0
        mg_upper_bound = np.max(self.demands) * np.max(self.affinity_matrix * (1 - self.constraint_matrix))

        if self.sample_size == 1:
            return sorted(list(range(n)), key=lambda x: random.random())

        while len(ordering) < n:
            next_agent = None
            best_usw = -np.inf

            sample_size = min(self.sample_size, len(available_agents))
            sorted_agents = sorted(random.sample(list(available_agents), sample_size))
            for a in sorted_agents:
                usw = self._compute_usw(ordering + [a])
                if usw is not None:
                    if usw > best_usw:
                        best_usw = usw
                        next_agent = a
                    if best_usw - curr_usw == mg_upper_bound:
                        break

            if next_agent is not None:
                curr_usw = best_usw
                ordering.append(next_agent)
                available_agents.remove(next_agent)
            else:
                # If unable to return an optimized order, return a random order
                return sorted(list(range(n)), key=lambda x: random.random())
        return ordering

    def solve(self):
        """Find an approximately optimal order and run round-robin assignment.

        Args:
            None

        Returns:
            The solution as a matrix.
        """

        self._validate_input_range()

        improper_papers = np.any(self.demands == 0)
        if improper_papers:
            proper_papers = np.where(self.demands > 0)[0]

            saved_demands = np.copy(self.demands)
            saved_constraint_matrix = np.copy(self.constraint_matrix)
            saved_affinity_matrix = np.copy(self.affinity_matrix)

            self.demands = self.demands[proper_papers]
            self.constraint_matrix = self.constraint_matrix[:, proper_papers]
            self.affinity_matrix = self.affinity_matrix[:, proper_papers]
            self.best_revs = self.best_revs[:, proper_papers]
            self.num_papers = self.num_papers - proper_papers.size

        ordering = self._select_ordering()
        self.logger.debug('Ordering is {}'.format(ordering))

        self.solution = self.safe_rr(ordering)

        if self.solution is None:
            self.logger.debug('GRRR was unable to find a WEF1 allocation satisfying all papers\' demands. '
                              'Falling back to picking sequence without WEF1 guarantees.')
            self.solution = self.rr(ordering)

            if self.solution is None:
                raise SolverException(
                    'Solver could not find a solution. Adjust your parameters.')

        if improper_papers:
            self.demands = saved_demands
            self.constraint_matrix = saved_constraint_matrix
            self.affinity_matrix = saved_affinity_matrix

            n = self.affinity_matrix.shape[0]
            idx = 0
            soln = np.zeros(self.affinity_matrix.shape, dtype=bool)
            for i in range(n):
                if i in proper_papers:
                    soln[:, i] = self.solution[:, idx]
                    idx += 1
            self.solution = soln

        self.logger.debug('USW: {}'.format(np.sum(self.affinity_matrix * self.solution)))

        self.solved = True
        return self.sol_as_mat().transpose()
