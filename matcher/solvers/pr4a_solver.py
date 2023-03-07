from gurobipy import Model, GRB, tupledict
from itertools import product
import numpy as np
import time
import logging
import random
import math
from .core import SolverException

class PR4ASolver:
    # tolerance for integrality check
    _EPS = 1e-3
    _GAMMA = 0.7
    _INITIAL_ALPHA = 0

    def __init__(self,
        minimums,
        maximums,
        demands,
        encoder,
        function=lambda x: x,
        iter_limit=1,
        time_limit=np.inf,
        logger=logging.getLogger(__name__),
        allow_zero_score_assignments=True,
        attr_constraints=None):
    # initialize the parameters
    # demand - requested number of reviewers per paper
    # ability - the maximum number of papers reviewer can review
    # function - transformation function of similarities
    # iter_limit - maximum number of iterations of Steps 2 to 7
    # time_limit - time limit in seconds. The algorithm performs iterations of Steps 2 to 7 until the time limit is exceeded
    # allow_zero_score_assignments - bool to allow pairs with zero affinity in the solution.
    # attr_constraints - expressions as constraints, commonly to require/upper/lower bound the number of a certain type of reviewer per paper
    
    # simmatrix, demand=3, ability=3, function=lambda x: x, iter_limit=np.inf, time_limit=np.inf):

        self.logger = logger
        self.logger.debug('Init PR4A')
        self.minimums = minimums
        self.abilities = maximums
        self.demands = demands
        self.demand = max(demands)
        self.constraint_matrix = encoder.constraint_matrix
        self.attr_constraints = attr_constraints
        # Example attr_constraints schema
        '''
        [{
            'name': 'Seniority',
            'bound': 1
            'members': [bool] * len(reviewers)
        }]
        '''

        # Probe constraints
        '''
        print('Checking updated expression constraints')
        for constraint_dict in self._balance_attributes:
            for _, constraint in constraint_dict.items():
                print(f"{self._problem.getRow(constraint)} {constraint.Sense} {constraint.RHS}")
        '''

        # Modify simmatrix with respect to constraint matrix
        # 1) Get matrix where -1 when <= -1 in the constraints and 0 elsewhere
        # 2) Get matrix with similarity when > -1 in the constraints, 0 elsewhere
        # 3) Add the matricies

        conflict_sims = encoder.constraint_matrix.T * (encoder.constraint_matrix <= -1).T
        allowed_sims = encoder.aggregate_score_matrix.transpose() * (encoder.constraint_matrix > -1).T
        self.simmatrix = conflict_sims + allowed_sims ## R x P
        self.numrev = self.simmatrix.shape[0]
        self.numpapers = self.simmatrix.shape[1]

        if not allow_zero_score_assignments:
            # Find reviewers with no non-zero affinity edges after constraints are applied and remove their load_lb
            bad_affinity_reviewers = np.where(
                np.all(
                    (self.simmatrix * (self.constraint_matrix == 0).T)
                    == 0,
                    axis=1,
                )
            )[0]
            print(bad_affinity_reviewers)

        # Validate demand
        for d in demands:
            if d != self.demand:
                raise SolverException('PR4A does not support custom paper demands, all demands must be the same')

        # TODO: Handle minimums
        # TODO: Handle custom demands

        self.function = function
        if iter_limit < 1:
            raise ValueError('Maximum number of iterations must be at least 1')
        self.iter_limit = iter_limit
        self.time_limit = time_limit
        self.solved = False

        self.logger.debug(f"Number of reviewers: {self.numrev}")
        self.logger.debug(f"Number of papers: {self.numpapers}")
        self.logger.debug("End Init PR4A")

    def _validate_input_range(self):
        """Validate if demand is in the range of min supply and max supply"""
        self.logger.debug("Checking if demand is in range")

        min_supply = sum(self.minimums)
        max_supply = sum(self.abilities)
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

    # initialize the flow network in the subroutine
    def _initialize_model(self):    
        
        self.logger.debug("Initializing model")
        problem = Model()
        problem.setParam('OutputFlag', False)

        # edges from source to reviewers, capacity controls maximum reviewer load

        self._source_vars = problem.addVars(list(range(self.numrev)), vtype=GRB.CONTINUOUS, lb=0.0,
                                            ub=self.abilities, name='reviewers')

        # edges from papers to sink, capacity controls a number of reviewers per paper

        self._sink_vars = problem.addVars(list(range(self.numpapers)), vtype=GRB.CONTINUOUS, lb=0.0,
                                          ub=self.demands, name='papers')

        # edges between reviewers and papers. Initially capacities are set to 0 (no edge is added in the network)

        self._mix_vars = problem.addVars(self.numrev, self.numpapers, vtype=GRB.CONTINUOUS,
                                         lb=0.0, ub=0.0, name='assignment')

        problem.update()

        # flow balance equations for reviewers' nodes
        self._balance_reviewers = problem.addConstrs((self._source_vars[i] == self._mix_vars.sum(i, '*')
                                                      for i in range(self.numrev)))

        # flow balance equations for papers' nodes
        self._balance_papers = problem.addConstrs((self._sink_vars[i] == self._mix_vars.sum('*', i)
                                                   for i in range(self.numpapers)))

        # Initialize attribute constraints and their initial bounds
        self._balance_attributes = []
        self._attribute_bounds = []
        if self.attr_constraints is not None:
            for constraint_dict in self.attr_constraints:
                bound, has_attr = constraint_dict['bound'], constraint_dict['members']
                members_with_attr = [idx for idx, attr_val in enumerate(has_attr) if attr_val]
                self._attribute_bounds.append([bound] * self.numpapers)

                self._balance_attributes.append(
                    problem.addConstrs((self._mix_vars.sum(members_with_attr, i) <= bound
                                                for i in range(self.numpapers)))
                )
                problem.update()

        problem.update()

        self._problem = problem

        self.logger.debug("End initializing model")

    # compute the order in which subroutine adds edges to the network
    def _ranking_of_pairs(self, simmatrix):
        pairs = [[reviewer, paper] for (reviewer, paper) in product(range(self.numrev), range(self.numpapers))]
        sorted_pairs = sorted(pairs, key=lambda x: simmatrix[x[0], x[1]], reverse=True)
        return sorted_pairs

    # subroutine
    # simmatrix - similarity matrix, updated for previously assigned papers
    # kappa - requested number of reviewers per paper
    # abilities - current constraints on reviewers' loads
    # not_assigned - a set of papers to be assigned
    # lower_bound - internal variable to start the binary search from
    def _subroutine(self, simmatrix, kappa, abilities, not_assigned, lower_bound, *args):
        
        gurobi_time = 0

        # set up the max flow objective
        self.logger.debug(f"Running subroutine for assignment demand {kappa}")
        self._problem.setObjective(sum([self._source_vars[i] for i in range(self.numrev)]), GRB.MAXIMIZE)

        # if paper is not fixed in the final output yet, assign it with kappa reviewers
        for paper in not_assigned:
            self._sink_vars[paper].ub = kappa
            self._sink_vars[paper].lb = 0

        # adjust reviewers' loads (in the network) for paper that are already fixed in the final assignment
        for reviewer in range(self.numrev):
            self._source_vars[reviewer].ub = abilities[reviewer]

        sorted_pairs = self._ranking_of_pairs(simmatrix)

        # upper_bound - internal variable to start the binary search from
        if args != ():
            upper_bound = args[0]
        else:
            upper_bound = len(sorted_pairs)

        current_solution = 0

        # if upper_bound == lower_bound, do one iteration to add corresponding edges to the flow network
        one_iteration_done = False

        # binary search to find the minimum number of edges
        # with largest similarity that should be added to the network
        # to achieve the requested max flow

        while lower_bound < upper_bound or not one_iteration_done:
            one_iteration_done = True
            prev_solution = current_solution
            current_solution = lower_bound + (upper_bound - lower_bound) // 2

            # the next condition is to control the case when upper_bound - lower_bound = 1
            # then it must be the case that max flow is less then required
            if current_solution == prev_solution:
                if maxflow < len(not_assigned) * kappa and current_solution == lower_bound:
                    current_solution += 1
                    lower_bound += 1
                else:
                    raise ValueError('An error occured1')

            
            # if binary choice increased the current estimate, add corresponding edges to the network
            if current_solution > prev_solution:
                for cur_pair in sorted_pairs[prev_solution: current_solution]:
                    self._mix_vars[cur_pair[0], cur_pair[1]].ub = 1
            # otherwise remove the corresponding edges
            else:
                for cur_pair in sorted_pairs[current_solution: prev_solution]:
                    self._mix_vars[cur_pair[0], cur_pair[1]].ub = 0

            # check maxflow in the current estimate
            start = time.time()
            self._problem.optimize()
            gurobi_time += (time.time() - start)
            #self.logger.debug(f"Gurobi Step (1): {time.time() - start:.2f} seconds")
            maxflow = self._problem.objVal

            # if maxflow equals to the required flow, decrease the upper bound on the solution
            if maxflow == len(not_assigned) * kappa:
                upper_bound = current_solution
            # otherwise increase the lower bound
            elif maxflow < len(not_assigned) * kappa:
                lower_bound = current_solution
            else:
                raise ValueError('An error occured2')

        # check if binary search succesfully converged
        if maxflow != len(not_assigned) * kappa or lower_bound != current_solution:
            # shouldn't enter here
            #print
            #maxflow, len(not_assigned), lower_bound, current_solution
            raise ValueError('An error occured3')

        # prepare for max-cost max-flow -- we enforce each paper to be reviewed by kappa reviewers
        for paper in not_assigned:
            self._sink_vars[paper].lb = kappa

        # max cost max flow objective
        self._problem.setObjective(sum([sum([simmatrix[reviewer, paper] * self._mix_vars[reviewer, paper]
                                             for paper in not_assigned])
                                        for reviewer in range(self.numrev)]), GRB.MAXIMIZE)
        start = time.time()
        self._problem.optimize()
        gurobi_time += (time.time() - start)
        #self.logger.debug(f"Gurobi Step (2): {time.time() - start:.2f} seconds")

        # return assignment
        assignment = {}
        for paper in not_assigned:
            assignment[paper] = []
        for reviewer in range(self.numrev):
            for paper in not_assigned:
                if self._mix_vars[reviewer, paper].X == 1:
                    assignment[paper] += [reviewer]
                if np.abs(self._mix_vars[reviewer, paper].X - int(self._mix_vars[reviewer, paper].X)) > self._EPS:
                    raise ValueError('Error with rounding -- please check that demand and ability are integal')
                self._mix_vars[reviewer, paper].ub = 0
        self._problem.update()

        self.logger.debug(f"Ending subroutine")

        return assignment, current_solution, gurobi_time

    # Join two assignments
    @staticmethod
    def _join_assignment(assignment1, assignment2):
        assignment = {}
        for paper in assignment1:
            assignment[paper] = assignment1[paper] + assignment2[paper]
        return assignment

    # Compute fairness
    def quality(self, assignment, *args):
        qual = np.inf
        if args != ():
            paper = args[0]
            return np.sum([self.function(self.simmatrix[reviewer, paper]) for reviewer in assignment[paper]])
        else:
            for paper in assignment:
                if qual > sum([self.function(self.simmatrix[reviewer, paper]) for reviewer in assignment[paper]]):
                    qual = np.sum([self.function(self.simmatrix[reviewer, paper]) for reviewer in assignment[paper]])
        return qual

    # Full algorithm
    def _fair_assignment(self):
        
        self.logger.debug(f"Starting PR4A algorithm")
        # Counter for number of performed iterations
        iter_counter = 0
        # Start time
        start_time = time.time()
        
        current_best = None
        current_best_score = 0
        local_simmatrix = self.simmatrix.copy()
        local_abilities = self.abilities.copy()
        not_assigned = set(range(self.numpapers))
        final_assignment = {}

        # One iteration of Steps 2 to 7 of the algorithm
        while not_assigned != set() and iter_counter < self.iter_limit and (time.time() < start_time + self.time_limit or iter_counter == 0):
            
            iter_counter += 1
            iter_start = time.time()
            self.logger.debug(f"PR4A Iteration: {iter_counter}")
            gurobi_time = 0
            time_labels = ['2a', '2b', '2c', '2d', '2e', '4-6']
            time_vals = [0] * len(time_labels)

            alpha = self._INITIAL_ALPHA if iter_counter == 1 else alpha
            delta_alpha = 0 if iter_counter == 1 else delta_alpha
            nu = 0 if iter_counter == 1 else nu
            
            lower_bound = 0
            upper_bound = len(not_assigned) * self.numrev

            # Step 2
            for kappa in range(1, self.demand + 1):

                # Beginning demand attempt - for all attributes set constraints to stored bounds
                if self.attr_constraints is not None:
                    for idx, constraint_dict in enumerate(self.attr_constraints):
                        attribute_bounds = self._attribute_bounds[idx]
                        has_attr = constraint_dict['members']
                        members_with_attr = [idx for idx, attr_val in enumerate(has_attr) if attr_val]

                        # Reset all paper constraints
                        for paper_idx in self._balance_attributes[idx].keys():
                            self._balance_attributes[idx][paper_idx].RHS = attribute_bounds[paper_idx]
                            self._problem.update()

                # Step 2(a)
                tmp_start = time.time()
                tmp_abilities = local_abilities.copy()
                tmp_simmatrix = local_simmatrix.copy()
                time_vals[0] = time.time() - tmp_start

                # Step 2(b)
                tmp_start = time.time()
                assignment1, lower_bound, g_time = self._subroutine(tmp_simmatrix, kappa, tmp_abilities, not_assigned, lower_bound, upper_bound)
                gurobi_time += g_time
                time_vals[1] = time.time() - tmp_start

                # Step 2(c)
                tmp_start = time.time()
                for paper in assignment1:
                    for reviewer in assignment1[paper]:
                        tmp_simmatrix[reviewer, paper] = -1
                        tmp_abilities[reviewer] -= 1

                        # Check if the attribute constraints need updating - this is to keep
                        # continuity of the constraints between these 2 separate matchings when they are added
                        if self.attr_constraints is not None:
                            for idx, meta_constraint_dict in enumerate(self.attr_constraints):
                                has_attr = meta_constraint_dict['members']
                                members_with_attr = [idx for idx, attr_val in enumerate(has_attr) if attr_val]

                                # For each attribute, if the assigned reviewer has this attribute
                                # decrement the RHS of this attribute constraint
                                if reviewer in members_with_attr:
                                    self._balance_attributes[idx][paper].RHS = max(self._balance_attributes[idx][paper].RHS - 1, 0)
                                    self._problem.update()
                time_vals[2] = time.time() - tmp_start

                # Step 2(d)
                tmp_start = time.time()
                assignment2, _, g_time = self._subroutine(tmp_simmatrix, self.demand - kappa, tmp_abilities, not_assigned, lower_bound, upper_bound)
                gurobi_time += g_time
                time_vals[3] = time.time() - tmp_start

                # Step 2(e)
                tmp_start = time.time()
                assignment = self._join_assignment(assignment1, assignment2)
                time_vals[4] = time.time() - tmp_start

                # Keep track of the best candidate assignment (including the one from the prev. iteration)
                if self.quality(assignment) > current_best_score or current_best_score == 0:
                    current_best = assignment
                    current_best_score = self.quality(assignment)

            self.logger.debug(f"Finish iterating through possible demands")

            # Steps 4 to 6
            tmp_start = time.time()

            ## NOTE: TESTING LOSSY ALGORITHM
            initial_not_assigned = len(not_assigned)

            for paper in not_assigned.copy():
                # For every paper not yet fixed in the final assignment we update the assignment
                final_assignment[paper] = current_best[paper]
                # Find the most worst-off paper
                if self.quality(current_best, paper) <= (current_best_score * (1 + alpha)):
                    # Delete it from current candidate assignment and from the set of papers which are
                    # not yet fixed in the final output
                    del current_best[paper]
                    not_assigned.discard(paper)
                    # This paper is now fixed in the final assignment

                    # Update abilities of reviewers
                    for reviewer in range(self.numrev):
                        # edges adjunct to the vertex of the most worst-off papers
                        # will not be used in the flow network any more
                        local_simmatrix[reviewer, paper] = -1
                        self._mix_vars[reviewer, paper].ub = 0
                        self._mix_vars[reviewer, paper].lb = 0
                        if reviewer in final_assignment[paper]:
                            # This reviewer assignment is finalized, reduce the stored bounds
                            # The change to the stored bounds will propagate back up to the main loop
                            if self.attr_constraints is not None:
                                for idx, meta_constraint_dict in enumerate(self.attr_constraints):
                                    has_attr = meta_constraint_dict['members']
                                    members_with_attr = [idx for idx, attr_val in enumerate(has_attr) if attr_val]

                                    # If the assigned reviewer has the flagged attribute,
                                    # decrement this paper's stored bound
                                    if reviewer in members_with_attr:
                                        self._attribute_bounds[idx][paper] = max(self._attribute_bounds[idx][paper] - 1, 0)
                                        self._problem.update()

                            local_abilities[reviewer] -= 1
            # Update alpha
            self.logger.debug(f"alpha: {alpha}")
            frac_papers_total_assigned = 1 - (len(not_assigned) / self.numpapers)
            frac_papers_assigned = (initial_not_assigned - len(not_assigned)) / initial_not_assigned
            alpha_proposed = (1 - 0.85*frac_papers_total_assigned) * (math.exp(-9 * (frac_papers_assigned + 0.05)) + 0.008)
            alpha = alpha_proposed if iter_counter == 1 else self._GAMMA * alpha + (1 - self._GAMMA) * alpha_proposed
            self.logger.debug(f"x (frac_assigned): {frac_papers_assigned}")
            self.logger.debug(f"y (frac_total_assigned): {frac_papers_total_assigned}")
            self.logger.debug(f"new alpha: {alpha}")

            time_vals[5] = time.time() - tmp_start
            self.logger.debug(f"{len(not_assigned) / self.numpapers * 100:.2f}% ({len(not_assigned)}/{self.numpapers}) of papers left to be assigned")
            self.logger.debug(f"Iteration finished in {(time.time() - iter_start)/60:.2f} minutes")
            self.logger.debug(f"Time taken by Gurobi: {gurobi_time/(time.time() - iter_start)*100:.2f}% ({gurobi_time/60:.2f}) minutes")
            self.logger.debug(','.join([str(e) for e in time_vals]))
            current_best_score = self.quality(current_best)
            self._problem.update()

        self.fa = final_assignment
        self.best_quality = self.quality(final_assignment)

        self.logger.debug(f"Ending PR4A algorithm")
        self.solved = True

    def solve(self):
        self._validate_input_range()
        self._initialize_model()
        self._fair_assignment()

        # Cast fair assignment to numpy
        assert len(self.fa.items()) > 0, "No solution"
        solved = np.zeros(
            (self.numrev, self.numpapers)
        )
        for reviewer_idx in self.fa.keys():
            for idx, paper_idx in enumerate(self.fa[reviewer_idx]):
                solved[paper_idx][reviewer_idx] = 1

        return solved.transpose()
