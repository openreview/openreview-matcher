from __future__ import print_function
import numpy as np

def build_arcs_simple(assignment_graph):
    '''
    3)  connect reviewer and paper nodes.
        exclude arcs between conflicted nodes.
    '''
    for r_node in assignment_graph.reviewer_nodes:
        for p_node in assignment_graph.paper_nodes:

            arc_cost = assignment_graph.cost_matrix[r_node.index,
                p_node.index]

            arc_constraint = assignment_graph.constraint_matrix[
                r_node.index, p_node.index]

            if arc_constraint in [0, 1]:
                assignment_graph.start_nodes.append(r_node)
                assignment_graph.end_nodes.append(p_node)
                assignment_graph.capacities.append(1)

                # arc_constraint of 0 means there's no constraint;
                # apply the cost as normal.
                if arc_constraint == 0:
                    assignment_graph.costs.append(int(arc_cost))

                # arc_constraint of 1 means that this user was explicitly
                # assigned to this paper;
                # set the cost as 1 less than the minimum cost.
                if arc_constraint == 1:
                    assignment_graph.costs.append(int(assignment_graph.min_cost - 1))

if __name__ == '__main__':
    from matcher.assignment_graph import AssignmentGraph
    cost_matrix = np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
        [2, 2, 1]
    ])
    constraint_matrix = np.zeros(np.shape(cost_matrix))
    graph = AssignmentGraph([1,1,1,1], [2,2,2,2], [1,1,2], cost_matrix, constraint_matrix, build_arcs=build_arcs_simple)
    graph.solve()

    print(graph)
