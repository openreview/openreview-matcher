from ortools.graph import pywrapgraph

import numpy as np
import uuid


class MinCostFlowMatcher(object):
    """Solves standard paper matching using max flow."""
    def __init__(self, alphas, betas, weights, constraints):
        """Initialize the matcher.

        Args:
            alphas - a list of integers specifying the maximum number of papers
                  for each reviewer.
            coverages - a list of integers specifying the number of reviews per
                 paper.
            weights - the affinity matrix (np.array) of papers to reviewers.
                   Rows correspond to reviewers and columns correspond to
                   papers.
            constraints - a set of tuples representing (rev, pap) constraints.

        Returns:
            initialized makespan matcher.
        """
        self.n_rev = np.size(weights, axis=0) # N, the number of reviewers
        self.n_pap = np.size(weights, axis=1) # M, the number of papers
        self.loads = alphas
        self.coverages = betas
        self.weights = weights
        self.constraints = constraints
        self.id = uuid.uuid4()
        self.solution = np.zeros((self.n_rev, self.n_pap))
        self.solved = False

        self.min_cost_flow = pywrapgraph.SimpleMinCostFlow()

        self.start_indices = []
        self.end_indices = []
        self.caps = []
        self.costs = []

        # Set the indices of the source and sink nodes.
        # Reviewer and paper nodes go from 0 to N+M-1.
        # We set the source and sink indices to N+M and N+M+1 to make iterating over paper and reviewer nodes more straightforward,
        # i.e. we can iterate over range(N+M).
        self.source_index = self.n_rev + self.n_pap
        self.sink_index = self.n_rev + self.n_pap + 1

        for i in range(self.n_rev):
            self.start_indices.append(self.source_index)
            self.end_indices.append(i)
            self.caps.append(int(self.loads[i]))
            self.costs.append(0)

        for i in range(self.n_rev):
            for j in range(self.n_pap):
                if (i, j) not in self.constraints:
                    self.start_indices.append(i)
                    self.end_indices.append(self.n_rev + j)
                    self.caps.append(1) # arcs from reviewers to papers have capacity 1 because a reviewer can only review a paper once.
                    # Next line is because the flow values have to be integers.
                    self.costs.append(int(-1.0 - 10000 * self.weights[i, j]))

        for j in range(self.n_pap):
            self.start_indices.append(self.n_rev + j)
            self.end_indices.append(self.sink_index)
            self.caps.append(int(self.coverages[j]))
            self.costs.append(0)

        self.supplies = np.zeros(self.n_rev + self.n_pap + 2)
        self.supplies[self.source_index] = int(sum(self.coverages))
        self.supplies[self.sink_index] = int(-sum(self.coverages))

        for i in range(len(self.start_indices)):
            self.min_cost_flow.AddArcWithCapacityAndUnitCost(
                self.start_indices[i], self.end_indices[i], self.caps[i],
                self.costs[i])
        for i in range(len(self.supplies)):
            self.min_cost_flow.SetNodeSupply(i, int(self.supplies[i]))

    def solve(self):
        """Solve matching."""
        if self.min_cost_flow.Solve() == self.min_cost_flow.OPTIMAL:
            # print('Total cost = ', self.min_cost_flow.OptimalCost())
            # print()
            for arc in range(self.min_cost_flow.NumArcs()):
                # Can ignore arcs leading out of source or into sink.
                if self.min_cost_flow.Tail(arc) != self.source_index and \
                                self.min_cost_flow.Head(arc) != self.sink_index:
                    if self.min_cost_flow.Flow(arc) > 0:
                        rev = self.min_cost_flow.Tail(arc)
                        pap = self.min_cost_flow.Head(arc) - self.n_rev
                        self.solution[rev, pap] = 1.0
            self.solved = True
        else:
            print('There was an issue with the min cost flow input.')

    def sol_as_mat(self):
        if self.solved:
            return self.solution
        else:
            raise Exception(
                'You must have solved the model optimally or suboptimally '
                'before calling this function.')

    def var_name(self, i, j):
        return "x_" + str(i) + "," + str(j)

    def sol_dict(self):
        _sol = {}
        for i in range(len(self.solution)):
            for j in range(len(self.solution[0])):
                if self.solution[i][j] == 1.0:
                    _sol[self.var_name(i, j)] = 1.0
                else:
                    assert self.solution[i][j] == 0.0
        return _sol


if __name__ == '__main__':
    costs = np.array([[.1, .9, .3],
                      [.1, .4, .2],
                      [.1, .14, .5],
                      [.7, .1, .7]])
    m = MinCostFlowMatcher(np.array([3, 3, 3, 3]), np.array([2, 2, 2]), costs,
                           set())
    m.solve()
    print(m)
    print(m.solution)
    print(m.sol_dict())
    print(m.start_indices)
    print(m.end_indices)
    print(m.source_index)
    print(m.sink_index)
