from __future__ import print_function
import numpy as np

from matcher.assignment_graph import GraphBuilder

class SimpleGraphBuilder(GraphBuilder):
    '''
    Adds edges to the assignment graph to implement the simple maximizer
    objective (maximizes the sum of scores)
    '''
    def build(self, graph):
        '''
        3)  connect reviewer and paper nodes.
            exclude arcs between conflicted nodes.
        '''
        for r_node in graph.reviewer_nodes:
            for p_node in graph.paper_nodes:

                arc_cost = graph.cost_matrix[r_node.index,
                    p_node.index]

                arc_constraint = graph.constraint_matrix[
                    r_node.index, p_node.index]

                if arc_constraint in [0, 1]:

                    # arc_constraint of 0 means there's no constraint;
                    # apply the cost as normal.
                    if arc_constraint == 0:
                        cost = int(arc_cost)

                    # arc_constraint of 1 means that this user was explicitly
                    # assigned to this paper;
                    # set the cost as 1 less than the minimum cost.
                    if arc_constraint == 1:
                        cost = int(graph.min_cost - 1)

                    graph.add_edge(r_node, p_node, 1, cost)
