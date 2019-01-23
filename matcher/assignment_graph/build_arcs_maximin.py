from __future__ import print_function
from itertools import product
from copy import deepcopy

import numpy as np

def _sorted_pairs(assignment_graph, sim_matrix):
    pairs = [[reviewer, paper] for (reviewer, paper) in product(range(assignment_graph.num_reviewers), range(assignment_graph.num_papers))]
    sorted_pairs = sorted(pairs, key=lambda x: sim_matrix[x[0], x[1]], reverse=True)
    return sorted_pairs

def _check_maxflow(sim_matrix, current_pairs, assignment_graph):
    '''
    Checks the flow across the assignment_graph, with the given pairs and similarity matrix.

    The cost of the arc from reviewer R to paper P is equal to their *similarity*, not their cost;
    in other words, the most similar paper-reviewer pairs are penalized the most.

    When the number of pairs being considered is as small as possible while still resulting in a
    feasible solution, it results in an assignment that maximizes the minimum scores across papers.
    '''
    graph_copy = deepcopy(assignment_graph)

    start_nodes = []
    end_nodes = []
    capacities = []
    costs = []

    for reviewer_index, paper_index in current_pairs:
        r_node = graph_copy.reviewer_node_by_index[reviewer_index]
        p_node = graph_copy.paper_node_by_index[paper_index]

        # cost is equal to similarity
        arc_cost = sim_matrix[r_node.index, p_node.index]

        arc_constraint = graph_copy.constraint_matrix[r_node.index, p_node.index]

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
                # costs.append(int(graph_copy.min_cost - 1))
                print('Something went wrong, this shouldn\'t happen')

    graph_copy.start_nodes += start_nodes
    graph_copy.end_nodes += end_nodes
    graph_copy.capacities += capacities
    graph_copy.costs += costs

    graph_copy.construct_solver()
    flow_matrix = graph_copy.solve()

    total_flow = np.sum(flow_matrix)

    return total_flow, start_nodes, end_nodes, capacities, costs

def _binsearch_for_parameters(sim_matrix, assignment_graph):
    '''
    Does a binary search on the sorted list of paper/reviewer pairs for current_solution,
    where current_solution is the fewest number of pairs that satisfies the requested demand,
    while adhering to the constraints.

    Returns the start/end nodes, capacities, and costs that represent arcs
    that match the solution found by the binary search.
    '''
    sorted_pairs = _sorted_pairs(assignment_graph, sim_matrix)

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
            if maxflow < sum(assignment_graph.demands) and current_solution == lower_bound:
                current_solution += 1
                lower_bound += 1
            else:
                raise ValueError('An error occured1')

        # check maxflow in the current estimate
        current_pairs = sorted_pairs[:current_solution]
        maxflow, start_nodes, end_nodes, capacities, costs = _check_maxflow(sim_matrix, current_pairs, assignment_graph)

        # if maxflow equals to the required flow, decrease the upper bound on the solution
        if maxflow == sum(assignment_graph.demands):
            upper_bound = current_solution

        # otherwise increase the lower bound
        elif maxflow < sum(assignment_graph.demands):
            lower_bound = current_solution
        else:
            raise ValueError('An error occured2')

    # check if binary search succesfully converged
    if maxflow != sum(assignment_graph.demands) or lower_bound != current_solution:
        # shouldn't enter here
        raise ValueError('An error occured3')

    return start_nodes, end_nodes, capacities, costs

def build_arcs_maximin(assignment_graph):

    sim_matrix = -1 * assignment_graph.cost_matrix
    # each sorted pair has the following form: [reviewer_index, paper_index]
    start_nodes, end_nodes, capacities, costs = _binsearch_for_parameters(sim_matrix, assignment_graph)

    assignment_graph.start_nodes += start_nodes
    assignment_graph.end_nodes += end_nodes
    assignment_graph.capacities += capacities
    assignment_graph.costs += costs

if __name__ == '__main__':

    from matcher.assignment_graph import AssignmentGraph

    cost_matrix = np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
        [2, 2, 1]
    ])
    constraint_matrix = np.zeros(np.shape(cost_matrix))
    graph = AssignmentGraph(
        [0,0,0,0],
        [2,2,2,2],
        [1,1,2],
        cost_matrix,
        constraint_matrix,
        build_arcs = build_arcs_maximin
        )
    graph.solve()

    print(graph)
