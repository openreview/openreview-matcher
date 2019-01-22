from __future__ import print_function, division
from ortools.graph import pywrapgraph
from collections import namedtuple
import numpy as np

Node = namedtuple('Node', ['number', 'index', 'supply'])
'''
"number" (0-indexed):
    a unique number among all Nodes in the graph.
    e.g. in a graph with 3 papers and 4 reviewers, number can take a
    value from 0 to 11.

"index" (0-indexed):
    a position in the cost/constraint matrix along the relevant axis
    e.g. in a graph with 3 papers and 4 reviewers, paper nodes can have
    "index" of value between 0 and 2, and reviewer nodes can have
    "index" of value between 0 and 3

"supply":
    an integer representing the supply (+) or demand (-) of a node.
'''

class AssignmentGraphError(Exception):
    pass

class AssignmentGraph:

    OPTIMAL = pywrapgraph.SimpleMinCostFlow.OPTIMAL

    '''
    Implements a min-cost network flow graph for the worker-task assignment problem
        (see: https://developers.google.com/optimization/flow/mincostflow)

    minimums/maximums: lists of length #reviewers. Each item in the lists is an
        integer representing the minimum/maximum number of reviews a reviewer
        should be assigned.

    demands: a list of integers of length #papers representing the number of
        reviews the paper should be assigned.

    cost_matrix: an #reviewers by #papers numpy array representing the cost of
        each reviewer-paper combination.

    constraint_matrix: an #reviewers by #papers numpy array representing
        constraints on the match. Each cell can take a value of -1, 0, or 1:

        0: no constraint
        1: strongly favor this pair
       -1: strongly avoid this pair

    **Inherited classes should implement the build_arcs function.**
    '''

    def __init__(self, minimums, maximums, demands, cost_matrix, constraint_matrix):

        self.solved = False

        assert type(cost_matrix) \
            == type(constraint_matrix) \
            == np.ndarray, \
            'cost and constraint matrices must be of type numpy.ndarray'

        assert np.shape(cost_matrix) \
            == np.shape(constraint_matrix), \
            'cost {} and constraint {} matrices must be the same shape'.format(
                np.shape(cost_matrix), np.shape(constraint_matrix))

        self.num_reviewers = np.size(cost_matrix, axis=0)
        self.num_papers = np.size(cost_matrix, axis=1)

        self.cost_matrix = cost_matrix
        self.constraint_matrix = constraint_matrix
        self.flow_matrix = np.zeros(np.shape(self.cost_matrix))
        # finds the largest and smallest value in cost_matrix
        # (i.e. the greatest and lowest cost of any arc)
        if self.cost_matrix.shape > (0,0):
            self.max_cost = self.cost_matrix[
                np.unravel_index(self.cost_matrix.argmax(), self.cost_matrix.shape)]
            self.min_cost = self.cost_matrix[
                np.unravel_index(self.cost_matrix.argmin(), self.cost_matrix.shape)]

        # maximums array must be same length as number of reviewers
        assert len(maximums) == self.num_reviewers, \
            'The length of the maximums array ({}) \
            must equal np.size(cost_matrix, axis=0) ({})'''.format(
            len(maximums), self.num_reviewers
        )
        self.maximums = maximums

        # minimums array must be same length as number of reviewers
        assert len(minimums) == self.num_reviewers, \
            'The length of the minimums array ({}) \
            must equal np.size(cost_matrix, axis=0) ({})'''.format(
            len(minimums), self.num_reviewers
        )
        self.minimums = minimums

        # demands array must be same length as number of papers
        assert len(demands) == self.num_papers, \
            'The length of the demands array ({}) \
            must equal np.size(cost_matrix, axis=0) ({})'.format(
            len(demands), self.num_papers)

        self.demands = demands
        supply = sum(self.maximums)
        demand = sum(self.demands)
        # the total supply of reviews must be greater than the total demand
        net_supply = supply + demand
        assert net_supply >= 0, \
            'demand exceeds supply (net supply: {})'.format(net_supply)



        current_offset = 0

        # no index because the source isn't represented in the cost/constraint matrices.
        self.source_node = Node(
            number = current_offset,
            index = None,
            supply = sum(self.demands))

        current_offset += 1

        self.free_review_nodes = [Node(
            number = i + current_offset,
            index = i,
            supply = 0) for i in range(self.num_reviewers)]

        current_offset += self.num_reviewers

        self.overflow_review_nodes = [Node(
            number = i + current_offset,
            index = i,
            supply = 0) for i in range(self.num_reviewers)]

        current_offset += self.num_reviewers

        self.reviewer_nodes = [Node(
            number = i + current_offset,
            index = i,
            supply = 0) for i in range(self.num_reviewers)]

        current_offset += self.num_reviewers

        self.paper_nodes = [Node(
            number = i + current_offset,
            index = i,
            supply = 0) for i in range(self.num_papers)]

        current_offset += self.num_papers

        # no index because the source isn't represented in the cost/constraint matrices.
        self.sink_node = Node(
            number = current_offset,
            index = None,
            supply = -1 * sum(self.demands))

        self.node_by_number = { n.number: n for n in \
            self.reviewer_nodes + \
            self.paper_nodes + \
            self.free_review_nodes + \
            self.overflow_review_nodes + \
            [self.source_node, self.sink_node] }

        free_nodes_by_index = {n.index: n for n in self.free_review_nodes}
        overflow_nodes_by_index = {n.index: n for n in self.overflow_review_nodes}

        self.reviewer_node_by_index = {n.index:n for n in self.reviewer_nodes}
        self.paper_node_by_index = {n.index:n for n in self.paper_nodes}

        '''
        Set up the flow graph.
        '''
        self.start_nodes = []
        self.end_nodes = []
        self.capacities = []
        self.costs = []

        '''
        1)  connect the source node to all "free" and "overflow" nodes.
        '''

        for free_node in self.free_review_nodes:
            self.start_nodes.append(self.source_node)
            self.end_nodes.append(free_node)
            self.capacities.append(self.minimums[free_node.index])
            self.costs.append(0)

        for overflow_node in self.overflow_review_nodes:
            self.start_nodes.append(self.source_node)
            self.end_nodes.append(overflow_node)
            self.capacities.append(
                self.maximums[overflow_node.index] - self.minimums[overflow_node.index])

            # TODO: Is this the right way to set the cost of the overflow?
            self.costs.append(int(self.max_cost + self.max_cost))

        '''
        2)  connect all "free" and "overflow" nodes to their corresponding
            reviewer nodes.
        '''
        for r_node in self.reviewer_nodes:
            free_node = free_nodes_by_index[r_node.index]
            self.start_nodes.append(free_node)
            self.end_nodes.append(r_node)
            self.capacities.append(self.minimums[r_node.index])
            self.costs.append(0)

            overflow_node = overflow_nodes_by_index[r_node.index]
            self.start_nodes.append(overflow_node)
            self.end_nodes.append(r_node)
            self.capacities.append(
                self.maximums[r_node.index] - self.minimums[r_node.index])
            self.costs.append(0)

        '''
        4)  connect paper nodes to the sink node.
        '''
        for p_node in self.paper_nodes:
            self.start_nodes.append(p_node)
            self.end_nodes.append(self.sink_node)
            self.capacities.append(self.demands[p_node.index])
            self.costs.append(0)

        assert len(self.start_nodes) \
            == len(self.end_nodes) \
            == len(self.capacities) \
            == len(self.costs), \
            '''start_nodes({}), end_nodes({}), capacities({}), and costs({})
            must all equal each other'''.format(
                len(self.start_nodes),
                len(self.end_nodes),
                len(self.capacities),
                len(self.costs),
                )

    def construct_solver(self):
        self.min_cost_flow = pywrapgraph.SimpleMinCostFlow()

        for arc_index in range(len(self.start_nodes)):
            self.min_cost_flow.AddArcWithCapacityAndUnitCost(
                self.start_nodes[arc_index].number,
                self.end_nodes[arc_index].number,
                self.capacities[arc_index],
                self.costs[arc_index]
            )

        for node in self.node_by_number.values():
            self.min_cost_flow.SetNodeSupply(node.number, node.supply)

    def solve(self):
        assert hasattr(self, 'min_cost_flow'), 'Solver not constructed. Run self.construct_solver() first.'

        if self.min_cost_flow.Solve() == self.min_cost_flow.OPTIMAL:
            self.solved = True
            for i in range(self.min_cost_flow.NumArcs()):
                cost = self.min_cost_flow.Flow(i) * self.min_cost_flow.UnitCost(i)
                t_node = self.node_by_number[self.min_cost_flow.Tail(i)]
                h_node = self.node_by_number[self.min_cost_flow.Head(i)]
                flow = self.min_cost_flow.Flow(i)

                if t_node.index in self.reviewer_node_by_index and h_node.index in self.paper_node_by_index:
                    self.flow_matrix[t_node.index, h_node.index] = flow
        else:
            self.solved = False

        return self.flow_matrix

    def build_arcs(self):
        raise AssignmentGraphError('Classes that inherit from the AssignmentGraph should implement their own `build_arcs` function.')

    def __str__(self):
        return_lines = []
        return_lines.append('Minimum cost: {}'.format(self.min_cost_flow.OptimalCost()))
        return_lines.append('')
        return_lines.append('   Arc    Flow / Capacity  Cost')
        for i in range(self.min_cost_flow.NumArcs()):
            cost = self.min_cost_flow.Flow(i) * self.min_cost_flow.UnitCost(i)
            return_lines.append('%2s -> %2s   %3s  / %3s       %3s' % (
              self.min_cost_flow.Tail(i),
              self.min_cost_flow.Head(i),
              self.min_cost_flow.Flow(i),
              self.min_cost_flow.Capacity(i),
              cost))
        return '\n'.join(return_lines)
