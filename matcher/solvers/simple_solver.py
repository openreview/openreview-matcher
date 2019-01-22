from __future__ import print_function
import numpy as np

from matcher.solvers.assignment_graph import AssignmentGraph

class SimpleSolver(AssignmentGraph):

    '''
    A simple min-cost flow assignment solver.

    Maximizes the sum total of affinity scores, subject to constraints.
    '''

    def __init__(self, minimums, maximums, demands, cost_matrix, constraint_matrix):

        AssignmentGraph.__init__(self, minimums, maximums, demands, cost_matrix, constraint_matrix)

        self.build_arcs()
        self.construct_solver()

    def build_arcs(self):
        '''
        3)  connect reviewer and paper nodes.
            exclude arcs between conflicted nodes.
        '''
        for r_node in self.reviewer_nodes:
            for p_node in self.paper_nodes:

                arc_cost = self.cost_matrix[r_node.index,
                    p_node.index]

                arc_constraint = self.constraint_matrix[
                    r_node.index, p_node.index]

                if arc_constraint in [0, 1]:
                    self.start_nodes.append(r_node)
                    self.end_nodes.append(p_node)
                    self.capacities.append(1)

                    # arc_constraint of 0 means there's no constraint;
                    # apply the cost as normal.
                    if arc_constraint == 0:
                        self.costs.append(int(arc_cost))

                    # arc_constraint of 1 means that this user was explicitly
                    # assigned to this paper;
                    # set the cost as 1 less than the minimum cost.
                    if arc_constraint == 1:
                        self.costs.append(int(self.min_cost - 1))

if __name__ == '__main__':
    cost_matrix = np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
        [2, 2, 1]
    ])
    constraint_matrix = np.zeros(np.shape(cost_matrix))
    solver = SimpleSolver([1,1,1,1], [2,2,2,2], [1,1,2], cost_matrix, constraint_matrix)
    solver.solve()

    print(solver)
