from collections import defaultdict
from ortools.graph import pywrapgraph
import numpy as np
import random
import uuid
import time
from .core import SolverException
import logging


class GWEF1(object):
    """
    Assign reviewers using a modified version of the Greedy Reviewer Round-Robin algorithm
    from I Will Have Order! Optimizing Orders for Fair Reviewer Assignment
    (https://arxiv.org/abs/2108.02126). This algorithm outputs an assignment that satisfies
    the weighted envy-free up to 1 item (WEF1) criterion.

    Reviewer Round-Robin (RRR) attempts to create an allocation of reviewers that is fair
    according to the weighted envy-free up to 1 item (WEF1) criterion. Papers pick reviewers
    one-by-one, with priority given to the papers with the lowest ratio of allocation size to demand.
    Ties in priority are resolved by selecting the paper which can select the highest-affinity reviewer.
    Some constraints apply to the selection process - most importantly, no paper can choose a
    reviewer that would cause a WEF1 violation. If this procedure fails to discover a complete, WEF1 allocation,
    we try the picking sequence again, allowing WEF1 violations during the process.
    """

    def __init__(
            self,
            minimums,
            maximums,
            demands,
            encoder,
            allow_zero_score_assignments=False,
            solution=None,
            sample_size=1,
            logger=logging.getLogger(__name__),
    ):
        """
        Initialize a GWEF1 matcher

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
        self.logger.debug("Init GWEF1")
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
        self.max_affinity = np.max(self.affinity_matrix)

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
        self.solution = (
            solution
            if solution
            else np.zeros((self.num_reviewers, self.num_papers))
        )
        assert self.affinity_matrix.shape == self.solution.shape

        self.solved = False
        self.logger.debug("End Init GWEF1")

    def _validate_input_range(self):
        """Validate if demand is in the range of min supply and max supply,
        and forbids currently unsupported settings."""
        self.logger.debug("Checking if demand is in range")

        min_supply = np.sum(self.minimums)
        max_supply = np.sum(self.maximums)
        demand = np.sum(self.demands)

        self.logger.debug(
            "Total demand is ({}), min review supply is ({}), and max review supply is ({})".format(
                demand, min_supply, max_supply
            )
        )

        if demand > max_supply or demand < min_supply:
            raise SolverException(
                "Total demand ({}) is out of range when min review supply is ({}) "
                "and max review supply is ({})".format(
                    demand, min_supply, max_supply
                )
            )

        self.logger.debug("Finished checking input ranges")

    def objective_val(self):
        """Get the objective value of the RAP."""
        return np.sum(self.sol_as_mat() * self.orig_affinities)

    def sol_as_mat(self):
        if self.solved:
            return self.solution
        else:
            raise SolverException(
                "You must have executed solve() before calling this function"
            )

    def _is_valid_assignment(self, r, p, matrix_alloc, previous_attained_scores):
        """Ensure that we can assign reviewer r to paper p without breaking weighted envy-freeness up to 1 item.

        We have to check any paper p_prime that has chosen a reviewer which is worth less to it than the value
        of r to p_prime. If p_prime has only chosen better reviewers, then it will necessarily be WEF1.

        Args:
            r - (int) the id of the reviewer we want to add
            p - (int) the id of the paper to which we are adding r
            matrix_alloc - (2d numpy array) the current allocation
            previous_attained_scores - (1d numpy array) maps each paper to the lowest affinity for any reviewer it holds

        Returns:
            True if r can be assigned to p without violating WEF1, False otherwise.
        """
        papers_to_check_against = set()
        for rev in np.where(matrix_alloc[:, p])[0].tolist() + [r]:
            papers_to_check_against |= set(
                np.where(previous_attained_scores < self.affinity_matrix[rev, :])[0].tolist())

        for p_prime in papers_to_check_against:
            # p_prime's normalized value for p's bundle, if we add r and remove the max value
            other = np.sum(matrix_alloc[:, p] * self.affinity_matrix[:, p_prime])
            other += self.affinity_matrix[r, p_prime]
            max_val = np.max(matrix_alloc[:, p] * self.affinity_matrix[:, p_prime])
            max_val = max(max_val, self.affinity_matrix[r, p_prime])
            other -= max_val
            other /= self.demands[p]

            # p_prime's normalized value for own bundle
            curr = np.sum(matrix_alloc[:, p_prime] * self.affinity_matrix[:, p_prime])
            curr /= self.demands[p_prime]

            # check wef1
            if other > curr and not np.isclose(other, curr):
                return False

        return True

    def _restrict_if_necessary(
            self, reviewers_remaining, matrix_alloc
    ):
        """Determine the number of papers we can still assign to each reviewer

        If we have exactly enough remaining reviewer slots to satisfy reviewer
        minima, then we set the remaining reviewers to be exactly the reviewers
        that need their minima satisfied.

        Args:
            reviewers_remaining - (1d numpy array) maximum number of papers each reviewer can
                still be assigned
            matrix_alloc - (2d numpy array) the assignment of reviewers to papers (papers are the rows)

        Returns:
            New reviewers_remaining - either the same as the input if we have enough papers to satisfy
            reviewer minima, or the exact assignments required to meet minima otherwise.
        """
        remaining_demand = np.sum(self.demands) - np.sum(
            matrix_alloc
        )
        required_for_min = self.minimums - np.sum(matrix_alloc, axis=1)
        required_for_min[required_for_min < 0] = 0
        return (
            required_for_min
            if np.sum(required_for_min) >= remaining_demand
            else reviewers_remaining
        )

    def _select_next_paper(self, matrix_alloc, best_revs_map, current_reviewer_maximums, previous_attained_scores, safe_mode):
        """Select the next paper to pick a reviewer

        Each paper i has priority t_i/w_i, where t_i is the number of reviewers already
        assigned to paper i, and w_i is the total demand of paper i. The
        paper with lowest priority is chosen, with ties broken by selecting the paper which
        will select a reviewer with the highest affinity.
        For rationale, please see:
        Weighted Envy-Freeness in Indivisible Item Allocation by Chakraborty et al. 2020.

        Args:
            matrix_alloc - (2d numpy array) the assignment of reviewers to papers (papers are the columns)

        Returns:
            The index of the next paper to pick a reviewer
        """
        priorities = np.sum(matrix_alloc, axis=0) / self.demands

        # Pick the papers which have the lowest priority, and then find the one with the best mg.
        choice_set = np.where(np.isclose(priorities, np.min(priorities)))[0].tolist()

        next_paper = None
        next_rev = None
        next_mg = -10000

        for p in choice_set:
            removal_set = []
            for r in best_revs_map[p]:
                if current_reviewer_maximums[r] <= 0 or \
                        matrix_alloc[r, p] > 0.5 or \
                        self.constraint_matrix[r, p] != 0 or \
                        (np.isclose(self.affinity_matrix[r, p], 0) and not self.allow_zero_score_assignments):
                    removal_set.append(r)
                elif self.affinity_matrix[r, p] > next_mg:
                    # This agent might be the greedy choice.
                    # Check if this is a valid assignment, then make it the greedy choice if so.
                    # If not a valid assignment, go to the next reviewer for this agent.
                    if not safe_mode or self._is_valid_assignment(r, p, matrix_alloc, previous_attained_scores):
                        next_paper = p
                        next_rev = r
                        next_mg = self.affinity_matrix[r, p]
                        break
                else:
                    # This agent cannot be the greedy choice
                    break

            for r in removal_set:
                best_revs_map[p].remove(r)

            if next_mg == self.max_affinity:
                return next_paper, next_rev, best_revs_map
        return next_paper, next_rev, best_revs_map

    def greedy_wef1(self, safe_mode=True):
        """Compute a WEF1 assignment via a picking sequence. Papers select reviewers in order of the
        picking sequence defined by the paper:
        Weighted Envy-Freeness in Indivisible Item Allocation by Chakraborty et al. 2021.
        Ties in selection order are resolved by picking the paper which can achieve the highest affinity
        by selecting a new reviewer.

        Papers select their favorite remaining reviewer in each step,
        subject to constraints - papers cannot pick a reviewer which would
        cause another paper to have weighted envy up to more than 1 reviewer, and they
        cannot pick a reviewer which is forbidden by the predefined constraint_matrix.

        Args:
            None

        Returns:
            A 2d numpy array with a WEF1 partial allocation to the papers.
            The array has the same shape as self.affinity_matrix, with a 1 in the i, j
            entry when reviewer i is assigned to paper j (and 0 otherwise).
        """
        matrix_alloc = np.zeros(self.affinity_matrix.shape, dtype=bool)
        maximums_copy = self.maximums.copy()

        best_revs_map = {}
        for p in range(self.num_papers):
            best_revs_map[p] = self.best_revs[:, p].tolist()

        previous_attained_scores = np.ones(self.num_papers) * 1000

        while np.sum(matrix_alloc) < np.sum(self.demands):
            maximums_copy = self._restrict_if_necessary(maximums_copy, matrix_alloc)

            next_paper, next_rev, best_revs_map = \
                self._select_next_paper(matrix_alloc, best_revs_map, maximums_copy, previous_attained_scores, safe_mode)

            if next_paper is None:
                return None

            maximums_copy[next_rev] -= 1
            matrix_alloc[next_rev, next_paper] = 1
            previous_attained_scores[next_paper] = min(self.affinity_matrix[next_rev, next_paper],
                                                       previous_attained_scores[next_paper])

        return matrix_alloc

    def solve(self):
        """Run a WEF1 assignment that maximizes the affinity at each step.

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
            self.num_papers = proper_papers.size

        self.solution = self.greedy_wef1()

        if self.solution is None:
            self.logger.debug(
                "Unable to find a WEF1 allocation satisfying all papers' demands. "
                "Falling back to picking sequence without WEF1 guarantees."
            )
            self.solution = self.greedy_wef1(safe_mode=False)

            if self.solution is None:
                raise SolverException(
                    "Solver could not find a solution. Adjust your parameters."
                )

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

        self.logger.debug(
            "USW: {}".format(np.sum(self.affinity_matrix * self.solution))
        )

        self.solved = True
        return self.sol_as_mat().transpose()
