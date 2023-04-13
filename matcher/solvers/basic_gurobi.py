import numpy as np
import time
import uuid
import argparse

from gurobipy import *


class Basic(object):
    """Paper matching formulated as a linear program."""
    def __init__(self, loads, coverages, weights, country = None, institute = None, conflict = None, loads_lb=None):
        """Initialize the Basic matcher
        Args:
            loads - a list of integers specifying the maximum number of papers
                  for each reviewer.
            coverages - a list of integers specifying the number of reviews per
                 paper.
            weights - the affinity matrix (np.array) of papers to reviewers.
                   Rows correspond to reviewers and columns correspond to
                   papers.
            loads_lb - a list of integers specifying the min number of papers
                  for each reviewer (optional).
        Returns:
            initialized matcher.
        """
        self.n_rev = np.size(weights, axis=0)
        self.n_pap = np.size(weights, axis=1)
        self.loads = loads
        self.loads_lb = loads_lb
        self.coverages = coverages

        assert(np.sum(coverages) <= np.sum(loads))
        if loads_lb is not None:
            assert(np.sum(coverages) >= np.sum(loads_lb))

        self.weights = weights
        self.id = uuid.uuid4()
        self.m = Model("%s: basic matcher" % str(self.id))
        self.solution = None
        self.m.setParam('OutputFlag', 0)

        # Primal vars.
        start = time.time()
        coeff = list(self.weights.flatten())
        print('#info Basic:flatten %s' % (time.time() - start))
        self.lp_vars = self.m.addVars(self.n_rev, self.n_pap, vtype=GRB.BINARY,
                                      name='x', obj=coeff)
        self.m.update()
        print('#info Basic:Time to add vars %s' % (time.time() - start))

        # Objective.
        self.m.setObjective(self.m.getObjective(), GRB.MAXIMIZE)
        self.m.update()

        # Constraints.
        start = time.time()
        self.m.addConstrs((self.lp_vars.sum(r, '*') <= l
                           for r, l in enumerate(self.loads)), name='p')
        self.m.addConstrs((self.lp_vars.sum('*', p) == c
                           for p, c in enumerate(self.coverages)), name='r')
        if conflict is not None:
            self.m.addConstrs((self.lp_vars[i,j] == 0 for i in range(self.n_rev) for j in range(self.n_pap) if conflict[i,j] == 1), name="conflict")
        if institute is not None:
            self.m.addConstrs((self.lp_vars.sum(institute[i], j) <= 1 for j in range(self.n_pap) for i in range(len(institute))), name="inst")
        if country is not None:
            self.m.addConstrs(
                (self.lp_vars.sum(country[i], j) <= 1 for j in range(self.n_pap) for i in range(len(country))),name="country")

        if self.loads_lb is not None:
            self.m.addConstrs((self.lp_vars.sum(r, '*') >= l
                               for r, l in enumerate(self.loads_lb)))

        self.m.update()
        print('#info Basic:Time to add constraints %s' % (time.time() - start))

    @staticmethod
    def var_name(i, j):
        """The name of the variable corresponding to reviewer i and paper j."""
        return "x_" + str(i) + "," + str(j)

    @staticmethod
    def indices_of_var(v):
        """Get the indices associated with a particular var_name (above)."""
        name = v.varName
        indices = name[2:].split(',')
        i, j = int(indices[0]), int(indices[1])
        return i, j

    def solve(self):
        """Solve the ILP.
        If we were not able to solve the ILP optimally or suboptimally, then
        raise an error.  If we are able to solve the ILP, save the solution.
        Args:
            None.
        Returns:
            An np array corresponding to the solution.
        """
        self.m.optimize()
        if self.m.status == GRB.OPTIMAL:
            self.solution = self.sol_as_mat()
        if self.m.status == GRB.INFEASIBLE:
            print ("INFEASIBLE")
            vars = self.m.getVars()
            ubpen = [1.0] * self.m.numVars
            constraints = [const for const in self.m.getConstrs() if "country" in const.ConstrName or "inst" in const.ConstrName]
            rhspen = [1.0] * len(constraints)
            self.m.feasRelax(1, False, vars, None, ubpen, constraints, rhspen)
            self.m.optimize()
            self.solution = self.sol_as_mat()
        return self.solution

    def sol_as_mat(self):
        if self.m.status == GRB.OPTIMAL:
            if self.solution is None:
                self.solution = np.zeros((self.n_rev, self.n_pap))
            for key, var in self.lp_vars.items():
                self.solution[key[0], key[1]] = var.x
            return self.solution
        else:
            raise Exception('Must solve the model optimally before calling!')

    def status(self):
        """Return the status code of the solver."""
        return self.m.status

    def turn_on_verbosity(self):
        """Turn on vurbosity for debugging."""
        self.m.setParam('OutputFlag', 1)

    def objective_val(self):
        """Get the objective value of a solved lp."""
        return self.m.ObjVal
