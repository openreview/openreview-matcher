from __future__ import print_function
from itertools import product
from copy import deepcopy

import numpy as np

from assignment_graph import AssignmentGraph

import ipdb

class MaxiMinSolver(AssignmentGraph):

    '''
    A flow-based solver that maximizes the minimum scores across all papers.
    '''

    def __init__(self, maximums, demands, cost_matrix, constraint_matrix):

        # TODO: Verify that the costs for the min/max shunting mechanism
        # in the AssignmentGraph class is compatible with this solver.
        # For now, only maximums are supported. Setting minimums = maximums
        # circumvents any issues with the min/max shunting mechanism.
        minimums = maximums
        AssignmentGraph.__init__(self, minimums, maximums, demands, cost_matrix, constraint_matrix)

        self.sim_matrix = -1 * self.cost_matrix

        self.build_arcs()
        self.construct_solver()

    def _sorted_pairs(self):
        pairs = [[reviewer, paper] for (reviewer, paper) in product(range(self.num_reviewers), range(self.num_papers))]
        sorted_pairs = sorted(pairs, key=lambda x: self.sim_matrix[x[0], x[1]], reverse=True)
        return sorted_pairs

    def build_arcs(self):
        '''
        TODO: Fill in with the subroutine from PeerReview4All paper.
        '''

        # each sorted pair has the following form: [reviewer_index, paper_index]
        sorted_pairs = self._sorted_pairs()

        def _compute_maxflow(num_pairs):
            assignment_graph = deepcopy(self)
            current_pairs = sorted_pairs[:num_pairs]

            start_nodes = []
            end_nodes = []
            capacities = []
            costs = []

            for reviewer_index, paper_index in current_pairs:
                r_node = assignment_graph.reviewer_node_by_index[reviewer_index]
                p_node = assignment_graph.paper_node_by_index[paper_index]

                # cost is equal to similarity
                arc_cost = self.sim_matrix[r_node.index, p_node.index]

                arc_constraint = assignment_graph.constraint_matrix[r_node.index, p_node.index]

                if arc_constraint in [0, 1]:
                    start_nodes.append(r_node)
                    end_nodes.append(p_node)
                    capacities.append(1)

                    # arc_constraint of 0 means there's no constraint;
                    # apply the cost as normal.
                    if arc_constraint == 0:
                        costs.append(int(arc_cost))

                    # arc_constraint of 1 means that this user was explicitly
                    # assigned to this paper;
                    # set the cost as 1 less than the minimum cost.
                    # TODO: Fix this / make sure it works in this setting
                    if arc_constraint == 1:
                        # costs.append(int(assignment_graph.min_cost - 1))
                        print('Something went wrong, this shouldn\'t happen')

            assignment_graph.start_nodes += start_nodes
            assignment_graph.end_nodes += end_nodes
            assignment_graph.capacities += capacities
            assignment_graph.costs += costs

            assignment_graph.construct_solver()
            flow_matrix = assignment_graph.solve()

            total_flow = np.sum(flow_matrix)

            return total_flow, start_nodes, end_nodes, capacities, costs

        # do a binary search for the minimum number of pairs needed to achieve a satisfactory match.

        # upper_bound - internal variable to start the binary search from
        upper_bound = len(sorted_pairs)
        lower_bound = 0
        current_solution = 0
        prev_solution = None
        max_flow = None

        # binary search to find the minimum number of edges
        # with largest similarity that should be added to the network
        # to achieve the requested max flow
        while lower_bound < upper_bound:
            prev_solution = current_solution
            current_solution = lower_bound + (upper_bound - lower_bound) // 2 # use integer division

            # the next condition is to control the case when upper_bound - lower_bound = 1
            # then it must be the case that max flow is less than required
            if current_solution == prev_solution:
                if maxflow < sum(self.demands) and current_solution == lower_bound:
                    current_solution += 1
                    lower_bound += 1
                else:
                    raise ValueError('An error occured1')

            # check maxflow in the current estimate
            maxflow, start_nodes, end_nodes, capacities, costs = _compute_maxflow(current_solution)

            # if maxflow equals to the required flow, decrease the upper bound on the solution
            if maxflow == sum(self.demands):
                upper_bound = current_solution

            # otherwise increase the lower bound
            elif maxflow < sum(self.demands):
                lower_bound = current_solution
            else:
                raise ValueError('An error occured2')

        # check if binary search succesfully converged
        if maxflow != sum(self.demands) or lower_bound != current_solution:
            # shouldn't enter here
            raise ValueError('An error occured3')

        self.start_nodes += start_nodes
        self.end_nodes += end_nodes
        self.capacities += capacities
        self.costs += costs



if __name__ == '__main__':
    cost_matrix = np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
        [2, 2, 1]
    ])
    constraint_matrix = np.zeros(np.shape(cost_matrix))
    solver = MaxiMinSolver([2,2,2,2], [1,1,2], cost_matrix, constraint_matrix)
    solver.solve()

    print(solver)
