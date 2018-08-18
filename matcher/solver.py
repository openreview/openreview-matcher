import uuid
import gurobipy
import logging
import time
import numpy as np

class Solver(object):
    """
    An iterative paper matching problem instance that tries to maximize
    the sum total affinity of all reviewer paper matches
    Attributes:
      num_reviewers - the number of reviewers
      num_papers - the number of papers
      alphas - a list of tuples of (min, max) papers for each reviewer.
      betas - a list of tuples of (min, max) reviewers for each paper.
      weights - the compatibility between each reviewer and each paper.
                This should be a numpy matrix of dimension [num_reviewers x num_papers].
    """

    def __init__(self, alphas, betas, weights, constraints):
        self.num_reviewers = np.size(weights, axis=0)
        self.num_papers = np.size(weights, axis=1)
        self.alphas = alphas
        self.betas = betas
        self.weights = weights
        self.constraints = []
        self.id = uuid.uuid4()
        self.model = gurobipy.Model(str(self.id) + ": iterative b-matching")
        self.prev_sols = []
        self.prev_reviewer_affinities = []
        self.prev_paper_affinities = []
        self.model.setParam('OutputFlag', 0)

        # primal variables; set the objective
        obj = gurobipy.LinExpr()
        self.lp_vars = [[] for i in range(self.num_reviewers)]

        for i in range(self.num_reviewers):
            for j in range(self.num_papers):
                self.lp_vars[i].append(self.model.addVar(vtype=gurobipy.GRB.BINARY, name=self.var_name(i, j)))
                obj += self.weights[i][j] * self.lp_vars[i][j]

        self.model.update()
        self.model.setObjective(obj, gurobipy.GRB.MAXIMIZE)

        # reviewer constraints
        for r in range(self.num_reviewers):
            self.model.addConstr(sum(self.lp_vars[r]) >= self.alphas[r][0], "r_l" + str(r))
            self.model.addConstr(sum(self.lp_vars[r]) <= self.alphas[r][1], "r_u" + str(r))

        # paper constraints
        for p in range(self.num_papers):
            self.model.addConstr(sum([self.lp_vars[i][p]
                                  for i in range(self.num_reviewers)]) >= self.betas[p][0],
                             "p_l" + str(p))
            self.model.addConstr(sum([self.lp_vars[i][p]
                                  for i in range(self.num_reviewers)]) <= self.betas[p][1],
                             "p_u" + str(p))

        for (reviewer_index, paper_index), value in constraints.iteritems():
            self.constraints.append((reviewer_index, paper_index, value))
        self.add_hard_consts(constrs=self.constraints)

    def var_name(self, i, j):
        return "x_" + str(i) + "," + str(j)

    def sol_dict(self):
        _sol = {}
        for v in self.model.getVars():
            _sol[v.varName] = v.x
        return _sol

    def add_hard_const(self, i, j, log_file=None):
        """Add a single hard constraint to the model.
        CAUTION: if you have a list of constraints to add, use add_hard_constrs
        instead.  That function adds the constraints as a batch and will be
        faster.
        """
        solution = self.sol_dict()
        prevVal = solution[self.var_name(i, j)]
        if log_file:
            logging.info("\t(REVIEWER, PAPER) " + str((i, j)) + " CHANGED FROM: " + str(prevVal) + " -> " + str(
                abs(prevVal - 1)))
        self.model.addConstr(self.lp_vars[i][j] == abs(prevVal - 1), "h" + str(i) + ", " + str(j))

    def add_hard_consts(self, constrs, log_file=None):
        """Add a list of hard constraints to the model.
        Add a list of hard constraints in batch to the model.
        Args:
        constrs - a list of triples of (rev_idx, pap_idx, value).
        Returns:
        None.
        """
        for (rev, pap, val) in constrs:
            self.model.addConstr(self.lp_vars[rev][pap] == val,
                             "h" + str(rev) + ", " + str(pap))
        self.model.update()

    def num_diffs(self, sol1, sol2):
        count = 0
        for (variable, val) in sol1.items():
            if sol2[variable] != val:
                count += 1
        return count

    def solve(self, log_file=None):
        begin_opt = time.time()
        self.model.optimize()
        if self.model.status != gurobipy.GRB.OPTIMAL:
            raise Exception('This instance of matching could not be solved '
                            'optimally.  Please ensure that the input '
                            'constraints produce a feasible matching '
                            'instance.')

        end_opt = time.time()
        if log_file:
            logging.info("[SOLVER TIME]: %s" % (str(end_opt - begin_opt)))

        sol = {}
        for v in self.model.getVars():
            sol[v.varName] = v.x
        self.prev_sols.append(sol)
        self.save_reviewer_affinity()
        self.save_paper_affinity()

        return self.sol_dict()

    def status(self):
        return m.status

    def turn_on_verbosity(self):
        self.model.setParam('OutputFlag', 1)

    def save_reviewer_affinity(self):
        per_rev_aff = np.zeros((self.num_reviewers, 1))
        sol = self.sol_dict()
        for i in range(self.num_reviewers):
            for j in range(self.num_papers):
                per_rev_aff[i] += sol[self.var_name(i, j)] * self.weights[i][j]
        self.prev_reviewer_affinities.append(per_rev_aff)

    def save_paper_affinity(self):
        per_pap_aff = np.zeros((self.num_papers, 1))
        sol = self.sol_dict()
        for i in range(self.num_papers):
            for j in range(self.num_reviewers):
                per_pap_aff[i] += sol[self.var_name(j, i)] * self.weights[j][i]
        self.prev_paper_affinities.append(per_pap_aff)

    def objective_val(self):
        return self.model.ObjVal
