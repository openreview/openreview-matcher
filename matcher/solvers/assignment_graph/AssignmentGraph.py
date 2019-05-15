from __future__ import print_function, division
from ortools.graph import pywrapgraph
from collections import namedtuple
import numpy as np
import importlib

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

class GraphBuilder:
    '''
    Base class
    '''

    def __init__(self):
        pass

    def build(self, graph):
        '''
        Given an AssignmentGraph object `assignment_graph`,
        adds edges (and/or nodes?) to it.
        '''

        raise AssignmentGraphError(
            'GraphBuilder must implement `build()` function')

    @staticmethod
    def get_builder(class_name):
        builder_module = importlib.import_module('matcher.solvers.assignment_graph', class_name)
        builder_class = getattr(builder_module, class_name)
        builder_instance = builder_class()
        return builder_instance

class AssignmentGraph:
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
    '''

    def __init__(
        self,
        minimums,
        maximums,
        demands,
        cost_matrix,
        constraint_matrix,
        graph_builder):

        self._check_inputs(minimums, maximums, demands, cost_matrix, constraint_matrix, graph_builder)

        self.solved = False
        self.cost_matrix = cost_matrix
        self.constraint_matrix = constraint_matrix
        self.flow_matrix = np.zeros(np.shape(self.cost_matrix))
        self.maximums = maximums
        self.minimums = minimums
        self.demands = demands
        self.num_papers = np.size(cost_matrix, axis=1)
        self.num_reviewers = np.size(cost_matrix, axis=0)
        self.graph_builder = graph_builder
        self.current_offset = 0

        self.start_nodes = []
        self.end_nodes = []
        self.capacities = []
        self.costs = []
        self.node_by_number = {}

        self.max_cost = self._greatest_cost()
        self.min_cost = self._least_cost()

        '''
        Add Nodes
        '''

        # no index because the source isn't represented in the cost/constraint matrices.
        self.source_node = self.add_node(index=None, supply=sum(self.demands))

        # "free" and "overflow" nodes are part of the min/max functionality.
        self.free_review_nodes = [self.add_node(i) for i in range(self.num_reviewers)]
        self.overflow_review_nodes = [self.add_node(i) for i in range(self.num_reviewers)]

        self.reviewer_nodes = [self.add_node(i) for i in range(self.num_reviewers)]
        self.paper_nodes = [self.add_node(i) for i in range(self.num_papers)]

        # no index because the sink isn't represented in the cost/constraint matrices.
        self.sink_node = self.add_node(index=None, supply=(-1 * sum(self.demands)))

        # make various indexes for Nodes
        self.reviewer_node_by_index = {n.index:n for n in self.reviewer_nodes}
        self.paper_node_by_index = {n.index:n for n in self.paper_nodes}

        '''
        Add Edges
        '''

        # connect the source node to all "free" and "overflow" nodes.
        for free_node in self.free_review_nodes:
            capacity = self.minimums[free_node.index]
            self.add_edge(self.source_node, free_node, capacity, cost=0)

        for overflow_node in self.overflow_review_nodes:
            capacity = self.maximums[overflow_node.index] - self.minimums[overflow_node.index]
            overflow_cost = int(self.max_cost + self.max_cost)
            self.add_edge(self.source_node, overflow_node, capacity, overflow_cost)

        # connect all "free" and "overflow" nodes to their corresponding reviewer nodes.
        free_nodes_by_index = {n.index: n for n in self.free_review_nodes}
        overflow_nodes_by_index = {n.index: n for n in self.overflow_review_nodes}
        for r_node in self.reviewer_nodes:
            free_node = free_nodes_by_index[r_node.index]
            free_capacity = self.minimums[r_node.index]
            self.add_edge(free_node, r_node, free_capacity, cost=0)

            overflow_node = overflow_nodes_by_index[r_node.index]
            overflow_capacity = self.maximums[r_node.index] - self.minimums[r_node.index]
            self.add_edge(overflow_node, r_node, overflow_capacity, cost=0)

        # connect paper nodes to the sink node.
        for p_node in self.paper_nodes:
            capacity = self.demands[p_node.index]
            self.add_edge(p_node, self.sink_node, capacity, cost=0)

        self.graph_builder.build(self)
        self.construct_solver()

    def _check_inputs(self, minimums, maximums, demands, cost_matrix, constraint_matrix, graph_builder):
        num_reviewers = np.size(cost_matrix, axis=0)
        num_papers = np.size(cost_matrix, axis=1)

        if not (type(cost_matrix) == type(constraint_matrix) == np.ndarray):
            raise AssignmentGraphError(
                'cost and constraint matrices must be of type numpy.ndarray')

        if not np.shape(cost_matrix) == np.shape(constraint_matrix):
            raise AssignmentGraphError(
                'cost {} and constraint {} matrices must be the same shape'.format(
                    np.shape(cost_matrix), np.shape(constraint_matrix)))

        if not len(maximums) == num_reviewers:
            raise AssignmentGraphError(
                'maximums array must be same length ({}) as number of reviewers ({}) '.format(
                    len(maximums), num_reviewers))

        if not len(minimums) == num_reviewers:
            raise AssignmentGraphError(
                'minimums array must be same length ({}) as number of reviewers ({})'.format(
                    len(minimums), num_reviewers))

        if not len(demands) == num_papers:
            raise AssignmentGraphError(
                'demands array must be same length ({}) as number of papers ({})'.format(
                    len(demands), num_papers))

        supply = sum(maximums)
        demand = sum(demands)
        if supply < demand:
            raise AssignmentGraphError(
                'the total supply of reviews ({}) must be greater than the total demand ({})'.format(
                    supply, demand))

    def _check_graph_integrity(self):
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

    def _boundary_cost(self, boundary_function):
        # finds a boundary cost in the cost_matrix according to the function `boundary_function`
        if self.cost_matrix.shape > (0,0):
            cost_boundary = self.cost_matrix[
                np.unravel_index(boundary_function(), self.cost_matrix.shape)]
            return cost_boundary
        else:
            return None

    def _greatest_cost(self):
        # finds the greatest value in cost_matrix
        return self._boundary_cost(self.cost_matrix.argmax)

    def _least_cost(self):
        # finds the lowest value in cost_matrix
        return self._boundary_cost(self.cost_matrix.argmin)

    def add_node(self, index, supply=0):
        new_node = Node(
            number = self.current_offset,
            index = index,
            supply = supply
        )

        if new_node.number in self.node_by_number:
            raise AssignmentGraphError('Node {} already exists in assignment graph.'.format(new_node.number))
        else:
            self.node_by_number[new_node.number] = new_node
            self.current_offset += 1
            return new_node

    def add_edge(self, start_node, end_node, capacity, cost):
        self.start_nodes.append(start_node)
        self.end_nodes.append(end_node)
        self.capacities.append(capacity)
        self.costs.append(cost)

    def construct_solver(self):
        self._check_graph_integrity()
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
        self.cost = 0
        if self.min_cost_flow.Solve() == self.min_cost_flow.OPTIMAL:
            self.solved = True
            for i in range(self.min_cost_flow.NumArcs()):
                self.cost += self.min_cost_flow.Flow(i) * self.min_cost_flow.UnitCost(i)
                t_node = self.node_by_number[self.min_cost_flow.Tail(i)]
                h_node = self.node_by_number[self.min_cost_flow.Head(i)]
                flow = self.min_cost_flow.Flow(i)

                if t_node in self.reviewer_nodes and h_node in self.paper_nodes:
                    self.flow_matrix[t_node.index, h_node.index] = flow
        else:
            self.solved = False

        return self.flow_matrix

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

if __name__ == '__main__':
    cost_matrix = np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
        [2, 2, 1]
    ])
    constraint_matrix = np.zeros(np.shape(cost_matrix))
    assignment_graph = AssignmentGraph([1,1,1,1], [2,2,2,2], [1,1,2], cost_matrix, constraint_matrix)
    assignment_graph.solve()

    print(assignment_graph)
