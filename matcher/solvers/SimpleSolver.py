from matcher.solvers.assignment_graph.AssignmentGraph import AssignmentGraph
from matcher.solvers.assignment_graph.SimpleGraphBuilder import SimpleGraphBuilder

class SimpleSolver(AssignmentGraph):
    def __init__(self, minimums, maximums, demands, cost_matrix, constraint_matrix):
        super().__init__(
            minimums,
            maximums,
            demands,
            cost_matrix,
            constraint_matrix,
            graph_builder = SimpleGraphBuilder()
        )



