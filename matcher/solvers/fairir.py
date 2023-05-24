import numpy as np
import time
import uuid
import logging
import math
import json
import psutil
from .core import SolverException

from .basic_gurobi import Basic
from gurobipy import *
from scipy import sparse
from itertools import product

class FairIR(Basic):
    """Fair paper matcher via iterative relaxation.

    """

    def __init__(
        self,
        minimums,
        maximums,
        demands,
        encoder,
        thresh=0.0,
        ##thresh=0.005, ## default value for NeurIPS
        allow_zero_score_assignments=False,
        logger=logging.getLogger(__name__)
        ):
        """Initialize.

        Args:
            loads (maximums) - a list of integers specifying the maximum number of papers
                  for each reviewer.
            loads_lb (minimums) - a list of ints specifying the minimum number of papers
                  for each reviewer.
            coverages (demands) - a list of integers specifying the number of reviews per
                 paper.
            weights (stored in encoder) - the affinity matrix (np.array) of papers to reviewers.
                   Rows correspond to reviewers and columns correspond to
                   papers.

            Returns:
                initialized makespan matcher.
        """

        # TODO: To allow zero score assignment, add small epsilon to all zero valued entries to avoid loss of data
        #     : during sparsification

        conflict_sims = encoder.constraint_matrix.T * (encoder.constraint_matrix <= -1).T ## -1 where constraints are -1, 0 else
        forced_matrix = (encoder.constraint_matrix >= 1).T ## 1 where constraints are 1, 0 else
        allowed_sims = encoder.aggregate_score_matrix.transpose() * (encoder.constraint_matrix >= 0).T ## unconstrained sims
        weights = conflict_sims + allowed_sims ## R x P ## TODO: sparsify weights, build set of sparse tuples? group by paper?

        # Sparsify weights
        sparse_weights = sparse.coo_matrix(weights)
        zero_weights = not np.any(weights)

        if not zero_weights:
            weights_list = sparse_weights.data
            reviewer_idxs = sparse_weights.row
            paper_idxs = sparse_weights.col
        else:
            weights_list = [0] * np.size(weights)
            reviewer_idxs, paper_idxs = [], []
            for t in list(product(range(np.size(weights, axis=0)), range(np.size(weights, axis=1)))):
                reviewer_idxs.append(t[0])
                paper_idxs.append(t[1])

        self.papers_by_reviewer = {r: [] for r in reviewer_idxs}
        self.reviewers_by_paper = {p: [] for p in paper_idxs}
        self.weights_by_rp = {}
        self.rp_to_lp_idx = {r: {} for r in reviewer_idxs}
        for w, r, p in zip(weights_list, reviewer_idxs, paper_idxs):
            self.weights_by_rp[(r, p)] = w
            
        for r, p in zip(reviewer_idxs, paper_idxs):
            self.papers_by_reviewer[r].append(p)
            self.reviewers_by_paper[p].append(r)

        self.logger = logger
        self.n_rev = np.size(weights, axis=0)
        self.n_pap = np.size(weights, axis=1)
        self.solved = False
        self.loads = maximums
        self.loads_lb = minimums
        self.coverages = demands
        self.allow_zero_score_assignments = allow_zero_score_assignments
        self.weights = weights
        self.attr_constraints = encoder.attribute_constraints
        # Example attr_constraints schema
        '''
        [{
            'name': 'Seniority',
            'bound': 1,
            'comparator': '>=',
            'members': [reviewer_indicies]
        }]
        '''

        # Build set of forced tuples (r, p)
        forced_list = []
        for r in range(self.n_rev):
            for p in self.papers_by_reviewer[r]:
                if forced_matrix[r, p] == 1:
                    forced_list.append(
                        (r, p)
                    )

        if not self.allow_zero_score_assignments:
            # Find reviewers with no non-zero affinity edges after constraints are applied and remove their load_lb
            bad_affinity_reviewers = np.where(
                np.all(
                    (encoder.aggregate_score_matrix.T * (encoder.constraint_matrix == 0).T)
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
                self.loads_lb[rev_id] = 0

        self._log_and_profile('Setting up model')
        self.id = uuid.uuid4()
        self.m = Model("%s : FairIR" % str(self.id))
        self.m.setParam('Threads', 50)
        self.makespan = thresh
        self.solution = None

        self.m.setParam('OutputFlag', 0)

        self.load_ub_name = 'lib'
        self.load_lb_name = 'llb'
        self.cov_name = 'cov'
        self.ms_constr_prefix = 'ms'
        self.round_constr_prefix = 'round'

        # primal variables
        start = time.time()
        self.lp_vars = []
        for i in range(self.n_rev):
            self.lp_vars.append([])
            papers = self.papers_by_reviewer[i]
            for idx, j in enumerate(papers):
                self.rp_to_lp_idx[i][j] = idx
                self.lp_vars[i].append(self.m.addVar(ub=1.0,
                                                     name=self.var_name(i, j)))
        self.m.update()
        self._log_and_profile('#info FairIR:Time to add vars %s' % (time.time() - start))

        start = time.time()
        # set the objective
        obj = LinExpr()
        for i in range(self.n_rev):
            papers = self.papers_by_reviewer[i]
            for j in range(len(papers)):
                obj += self.weights[i][j] * self.lp_vars[i][j]
        self.m.setObjective(obj, GRB.MAXIMIZE)
        self._log_and_profile('#info FairIR:Time to set obj %s' % (time.time() - start))

        start = time.time()
        # load upper bound constraints.
        for r, load in enumerate(self.loads):
            self.m.addConstr(sum(self.lp_vars[r]) <= load,
                             self.lub_constr_name(r))

        # load load bound constraints.
        if self.loads_lb is not None:
            for r, load in enumerate(self.loads_lb):
                self.m.addConstr(sum(self.lp_vars[r]) >= load,
                                 self.llb_constr_name(r))

        # coverage constraints.
        for p, cov in enumerate(self.coverages):
            reviewers = self.reviewers_by_paper[p]
            self.m.addConstr(sum([self.lp_vars[i][self._paper_number_to_lp_idx(i, p)]
                                  for i in reviewers]) == cov,
                             self.cov_constr_name(p))

        self._log_and_profile('#info FairIR:Time to set loads and coverage %s' % (time.time() - start))

        # forced assignment constraints.
        for forced in forced_list:
            reviewer, paper = forced[0], forced[1]
            self.fix_assignment(reviewer, self._paper_number_to_lp_idx(reviewer, paper), 1)

        # attribute constraints.
        if self.attr_constraints is not None:
            self._log_and_profile(f"Attribute constraints detected")
            for constraint_dict in self.attr_constraints:
                constraint_start = time.time()
                name, bound, comparator, members = constraint_dict['name'], constraint_dict['bound'], constraint_dict['comparator'], constraint_dict['members']
                for p in range(self.n_pap):
                    reviewers = self.reviewers_by_paper[p]
                    overlap = set(reviewers).intersection(set(members))

                    # Check number of forced assignments and adjust bounds
                    num_forced = 0
                    for forced in forced_list:
                        if p == forced[1]:
                            num_forced += 1

                    remaining_demand = self.coverages[p] - num_forced

                    if comparator == '==':
                        adj_bound = bound if remaining_demand >= bound else remaining_demand
                        self.m.addConstr(sum([self.lp_vars[i][self._paper_number_to_lp_idx(i, p)]
                                    for i in overlap]) == adj_bound,
                                    self.attr_constr_name(name, p))
                    elif comparator == '>=':
                        adj_bound = bound if remaining_demand >= bound else remaining_demand
                        self.m.addConstr(sum([self.lp_vars[i][self._paper_number_to_lp_idx(i, p)]
                                    for i in overlap]) >= adj_bound,
                                    self.attr_constr_name(name, p))
                    elif comparator == '<=':
                        adj_bound = bound if num_forced <= bound else min(bound + num_forced, self.coverages[p])
                        self.m.addConstr(sum([self.lp_vars[i][self._paper_number_to_lp_idx(i, p)]
                                    for i in overlap]) <= adj_bound,
                                    self.attr_constr_name(name, p))
                self._log_and_profile(f"Time to add {len(members)} {name} constraints: {time.time() - constraint_start}")

                ## Don't call it for every consraint iteration
                ## self.m.update()

        # makespan constraints.
        for p in range(self.n_pap):
            reviewers = self.reviewers_by_paper[p]
            self.m.addConstr(sum([self.lp_vars[i][self._paper_number_to_lp_idx(i, p)] * self.weights[i][p]
                                  for i in reviewers]) >= self.makespan,
                             self.ms_constr_name(p))
        self.m.update()
        self._log_and_profile('#info FairIR:Time to add all constraints %s' % (time.time() - start))

    def _paper_number_to_lp_idx(self, rev_num, paper_num):
        papers = self.papers_by_reviewer[rev_num]
        try:
            return self.rp_to_lp_idx[rev_num][paper_num]
        except:
            raise SolverException(f"No score between paper {paper_num} and reviewer {rev_num}")

    def _log_and_profile(self, log_message=""):
        conv = 1e9
        vmem = psutil.virtual_memory()
        smem = psutil.swap_memory()
        self.logger.debug(f"{log_message} | Memory: {vmem.used/conv:.2f}/{vmem.available/conv:.2f}={vmem.percent}% | Swap Memory: {smem.used/conv:.2f}/{smem.total/conv:.2f}={smem.percent}%")

    def _validate_input_range(self):
        """Validate if demand is in the range of min supply and max supply"""
        self._log_and_profile("Checking if demand is in range")

        min_supply = sum(self.loads_lb)
        max_supply = sum(self.loads)
        demand = sum(self.coverages)

        self._log_and_profile(
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

        self._log_and_profile("Finished checking graph inputs")

    def attr_constr_name(self, n, p):
        """Name of the makespan constraint for paper p."""
        return '%s%s' % (n, p)

    def ms_constr_name(self, p):
        """Name of the makespan constraint for paper p."""
        return '%s%s' % (self.ms_constr_prefix, p)

    def lub_constr_name(self, r):
        """Name of load upper bound constraint for reviewer r."""
        return '%s%s' % (self.load_ub_name, r)

    def llb_constr_name(self, r):
        """Name of load lower bound constraint for reviewer r."""
        return '%s%s' % (self.load_lb_name, r)

    def cov_constr_name(self, p):
        """Name of coverage constraint for paper p."""
        return '%s%s' % (self.cov_name, p)

    def change_makespan(self, new_makespan):
        """Change the current makespan to a new_makespan value.

        Args:
            new_makespan - the new makespan constraint.

        Returns:
            Nothing.
        """
        self._log_and_profile('#info FairIR:CHANGE_MAKESPAN call')
        for c in self.m.getConstrs():
            if c.getAttr("ConstrName").startswith(self.ms_constr_prefix):
                self.m.remove(c)
                # self.m.update()

        for p in range(self.n_pap):
            reviewers = self.reviewers_by_paper[p]
            self.m.addConstr(sum([self.lp_vars[i][self._paper_number_to_lp_idx(i, p)] * self.weights[i][p]
                                  for i in reviewers]) >= new_makespan,
                             self.ms_constr_prefix + str(p))
        self.makespan = new_makespan
        self.m.update()
        self._log_and_profile('#info RETURN FairIR:CHANGE_MAKESPAN call')

    def sol_as_mat(self):
        self._log_and_profile('#info FairIR:SOL_AS_MAT call')
        if self.m.status == GRB.OPTIMAL or self.m.status == GRB.SUBOPTIMAL:
            self.solved = True
            solution = np.zeros((self.n_rev, self.n_pap))
            for v in self.m.getVars():
                i, j = self.indices_of_var(v)
                solution[i, j] = v.x
            self.solution = solution
            return solution
        else:
            raise Exception(
                'You must have solved the model optimally or suboptimally '
                'before calling this function.')

    def integral_sol_found(self, precalculated=None):
        self._log_and_profile('#info FairIR:INTEGRAL_SOL_FOUND call')
        """Return true if all lp variables are integral."""
        sol = self.sol_as_dict() if precalculated is None else precalculated
        return all(sol[self.var_name(i, j)] == 1.0 or
                   sol[self.var_name(i, j)] == 0.0
                   for i in range(self.n_rev) for j in self.papers_by_reviewer[i])

    def fix_assignment(self, i, j, val):
        """Round the variable x_ij to val."""
        self.lp_vars[i][j].ub = val
        self.lp_vars[i][j].lb = val
        
    def fix_assignment_to_one_with_constraints(self, i, j, integral_assignments):
        """Round the variable x_ij to 1 if the attribute constraints are obeyed : i - reviewer, j - paper"""
        # NOTE
        ## FIRST check integral assignments only - these should correspond to the true assignments
        ## SECOND check lb == 1 or ub == 0 to check for assignments
        if self.attr_constraints is not None:
            for constraint_dict in self.attr_constraints:
                bound, comparator, members =  constraint_dict['bound'], constraint_dict['comparator'], constraint_dict['members']
                s = sum([integral_assignments[k][j] for k in members]) + 1 ## s = current total + 1 more assignment

                # If leq constraint and adding 1 does not violate the bound, fix assignment
                if comparator == '<=' and s < bound:
                    self.fix_assignment(i, j, 1.0)
                    integral_assignments[i][j] = 1.0
        else:
            self.fix_assignment(i, j, 1.0)
            integral_assignments[i][j] = 1.0

    def fix_assignment_to_zero_with_constraints(self, i, j, integral_assignments):
        """Round the variable x_ij to 1 if the attribute constraints are obeyed : i - reviewer, j - paper"""
        # NOTE
        ## FIRST check integral assignments only - these should correspond to the true assignments
        ## SECOND check lb == 1 or ub == 0 to check for assignments
        if self.attr_constraints is not None:
            for constraint_dict in self.attr_constraints:
                bound, comparator, members =  constraint_dict['bound'], constraint_dict['comparator'], constraint_dict['members']
                s = sum([integral_assignments[k][j] for k in members]) + 1 ## s = current total + 1 more assignment

                # If geq or eq constraint and the bound is already satisfied, allow assignment to be 0
                if (comparator == '==' or comparator == '>=') and s >= bound:
                    self.fix_assignment(i, j, 0.0)
                    integral_assignments[i][j] = 0.0
        else:
            self.fix_assignment(i, j, 0.0)
            integral_assignments[i][j] = 0.0

    def find_ms(self):
        self._log_and_profile('#info FairIR:FIND_MS call')
        """Find an the highest possible makespan.

        Perform a binary search on the makespan value. Each time, solve the
        makespan LP without the integrality constraint. If we can find a
        fractional value to one of these LPs, then we can round it.

        Args:
            None

        Return:
            Highest feasible makespan value found.
        """
        mn = 0.0
        mx = np.max(self.weights) * np.max(self.coverages)
        ms = mx
        best = None
        self.change_makespan(ms)
        start = time.time()
        self.m.optimize()
        self._log_and_profile('#info FairIR:Time to solve %s' % (time.time() - start))
        for i in range(10):
            self._log_and_profile('#info FairIR:ITERATION %s ms %s' % (i, ms))
            if self.m.status == GRB.INFEASIBLE:
                mx = ms
                ms -= (ms - mn) / 2.0
            else:
                assert(best is None or ms >= best)
                assert(self.m.status == GRB.OPTIMAL)
                best = ms
                mn = ms
                ms += (mx - ms) / 2.0
            self.change_makespan(ms)
            start = time.time()
            self.m.optimize()
            self._log_and_profile('#info FairIR:Time to solve %s' % (time.time() - start))
        self._log_and_profile(f'#info RETURN FairIR:FIND_MS call ms={best}')

        if best is None:
            return 0.0
        else:
            return best

    def solve(self):
        self._log_and_profile('#info FairIR:SOLVE call')
        """Find a makespan and solve the ILP.

        Run a binary search to find an appropriate makespan and then solve the
        ILP. If solved optimally or suboptimally then save the solution.

        Args:
            mn - the minimum feasible makespan (optional).
            mx - the maximum possible makespan( optional).
            itr - the number of iterations of binary search for the makespan.
            log_file - the string path to the log file.

        Returns:
            The solution as a matrix.
        """
        self._validate_input_range()
        if self.makespan <= 0:
            self._log_and_profile('#info FairIR: searching for fairness threshold')
            ms = self.find_ms()
        else:
            self._log_and_profile('#info FairIR: config fairness threshold: %s' % self.makespan)
            ms = self.makespan
        self.change_makespan(ms)
        self.round_fraction_iteration()

        sol = {}
        for v in self.m.getVars():
            sol[v.varName] = v.x

        self._log_and_profile('#info RETURN FairIR:SOLVE call')
        return self.sol_as_mat().transpose()

    def sol_as_dict(self):
        self._log_and_profile('#info FairIR:SOL_AS_DICT call')
        """Return the solution to the optimization as a dictionary.

        If the matching has not be solved optimally or suboptimally, then raise
        an exception.

        Args:
            None.

        Returns:
            A dictionary from var_name to value (either 0 or 1)
        """
        if self.m.status == GRB.OPTIMAL or self.m.status == GRB.SUBOPTIMAL:
            self.solved = True
            _sol = {}
            for v in self.m.getVars():
                _sol[v.varName] = v.x
            return _sol
        else:
            raise Exception(
                'You must have solved the model optimally or suboptimally '
                'before calling this function.\nSTATUS %s\tMAKESPAN %f' % (
                    self.m.status, self.makespan))

    def round_fractional(self, integral_assignments, count=0):
        self._log_and_profile('#info FairIR:ROUND_FRACTIONAL call: %s' % count)
        """Round a fractional solution.

        This is the meat of the iterative relaxation approach.  First, if the
        solution to the relaxed LP is integral, then we're done--return the
        solution. Otherwise, here's what we do:
        1. if a variable is integral, lock it's value to that integer.
        2. find all papers with exactly 2 or 3 fractionally assigned revs and
           drop the makespan constraint on that reviewer.
        3. if no makespan constraints dropped, find a reviewer with exactly two
           fraction assignments and drop the load constraints on that reviewer.

        Args:
            integral_assignments - np.array of revs x paps (initially None).
            log_file - the log file if exists.
            count - (int) to keep track of the number of calls to this function.

        Returns:
            Nothing--has the side effect or storing an assignment matrix in this
            class.
        """

        start = time.time()
        self.m.optimize()

        self._log_and_profile('#info FairIR:Time to solve %s' % (time.time() - start))

        if self.m.status != GRB.OPTIMAL and self.m.status != GRB.SUBOPTIMAL:
            self.m.computeIIS()
            self.m.write("model.ilp")
            assert False, '%s\t%s' % (self.m.status, self.makespan)

        # Check that the constraints are obeyed when fetching sol
        # attribute constraints.
        self._log_and_profile('Checking if attribute constraints exist')
        sol = self.sol_as_dict()

        if self.integral_sol_found(precalculated=sol):
            return True
        else:
            frac_assign_p = {}
            frac_assign_r = {}
            fractional_vars = []

            fixed, frac = 0, 0

            # Find fractional vars.
            for i in range(self.n_rev):
                papers = self.papers_by_reviewer[i]
                for paper_idx, j in enumerate(papers):
                    if j not in frac_assign_p:
                        frac_assign_p[j] = []
                    if i not in frac_assign_r:
                        frac_assign_r[i] = []

                    if sol[self.var_name(i, j)] == 0.0 and integral_assignments[i][j] != 0.0:
                        #self.fix_assignment_to_zero_with_constraints(i, j, integral_assignments)
                        self.fix_assignment(i, paper_idx, 0.0)
                        integral_assignments[i][j] = 0.0
                        fixed += 1

                    elif sol[self.var_name(i, j)] == 1.0 and integral_assignments[i][j] != 1.0:
                        #self.fix_assignment_to_one_with_constraints(i, j, integral_assignments)
                        self.fix_assignment(i, paper_idx, 1.0)
                        integral_assignments[i][j] = 1.0
                        fixed += 1

                    elif sol[self.var_name(i, j)] != 1.0 and sol[self.var_name(i, j)] != 0.0:
                        frac_assign_p[j].append(
                            (i, j, sol[self.var_name(i, j)])
                        )
                        frac_assign_r[i].append(
                            (i, j, sol[self.var_name(i, j)])
                        )

                        fractional_vars.append((i, j, sol[self.var_name(i, j)]))
                        integral_assignments[i][j] = sol[self.var_name(i, j)]
                        frac += 1
                
            self._log_and_profile(f'#info FairIR:ROUND_FRACTIONAL END O(RP) loop\nfixed={fixed}, frac={frac}')

            # First try to elim a makespan constraint.
            removed = False
            self._log_and_profile(f'#info FairIR:ROUND_FRACTIONAL Relaxing local fairness n_papers={len(frac_assign_p.keys())}')
            for (paper, frac_vars) in frac_assign_p.items():
                if len(frac_vars) == 2 or len(frac_vars) == 3:
                    for c in self.m.getConstrs():
                        if c.ConstrName == self.ms_constr_name(paper):
                            self.m.remove(c)
                            removed = True

            # If necessary remove a load constraint.
            if not removed:
                for (rev, frac_vars) in frac_assign_r.items():
                    if len(frac_vars) == 2:
                        for c in self.m.getConstrs():
                            if c.ConstrName == self.lub_constr_name(rev) or \
                                      c.ConstrName == self.llb_constr_name(rev):
                                self.m.remove(c)
            self.m.update()

            self._log_and_profile('#info RETURN FairIR:ROUND_FRACTIONAL call')
            return False
        
    def round_fraction_iteration(self):
        integral_assignments = np.ones((self.n_rev, self.n_pap), dtype=np.float16) * -1
        demand = sum(self.coverages)
        for count in range(50):
            solved = self.round_fractional(integral_assignments, count)
            num_assigned = np.count_nonzero(integral_assignments == 1)
            self._log_and_profile(f"#info PROGRESS {num_assigned}/{demand}={num_assigned/demand:.2f}")
            if solved:
                return
        
        if not solved:
            raise Exception('No Solution.')
