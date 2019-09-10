import numpy as np
import time
import uuid

from gurobipy import *

class Basic(object):
    """Paper matching formulated as a linear program."""
    def __init__(self, loads, coverages, weights, loads_lb=None):
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
                           for r, l in enumerate(self.loads)))
        self.m.addConstrs((self.lp_vars.sum('*', p) == c
                           for p, c in enumerate(self.coverages)))
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


if __name__ == "__main__":
    init_makespan = 0.7
    ws = np.array([
        [0.1, 0.1, 0.9, 0.9],
        [0.1, 0.1, 0.9, 0.9],
        [0.1, 0.1, 0.6, 0.8],
        [0.1, 0.1, 0.4, 0.3]
    ])
    a = np.array([2, 2, 2, 2])
    b = np.array([2, 2, 2, 2])
    x = Basic(a, b, ws, loads_lb=None)
    s = time.time()
    x.solve()
    print(x.sol_as_mat())
    print(time.time() - s)
    print('[done.]')
