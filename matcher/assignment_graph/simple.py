from matcher.assignment_graph.objective_type import ObjectiveType

class Simple (ObjectiveType):


    def build (self, assignment_graph):
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
