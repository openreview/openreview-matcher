'''
Implements classes used to represent a minimum-cost flow graph for assigning papers to reviewers.
(see: https://developers.google.com/optimization/flow/mincostflow)

SimpleSolver is initialized with the following arguments:

    "num_reviews":
        lists of length #reviewers. Each item in the lists is an
        integer representing the number of reviews a reviewer
        can be assigned.

    "demands":
        a list of integers of length #papers representing the number of
        reviews the paper should be assigned.

    "cost_matrix":
        a #reviewers by #papers numpy array representing the cost of
        each reviewer-paper combination.

    "constraint_matrix":
        a #reviewers by #papers numpy array representing
        constraints on the match. Each cell can take a value of -1, 0, or 1:

        0: no constraint
        1: strongly favor this pair
       -1: strongly avoid this pair

    "strict":
        True (default) or False. If True, throws an error when the sum of
        the number of available reviews does not equal the sum of demands


Node is a namedtuple that is used to represent nodes in the graph:

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

from __future__ import print_function, division
from collections import namedtuple
import logging
import numpy as np
from ortools.graph import pywrapgraph
from .core import SolverException

Node = namedtuple('Node', ['number', 'index', 'supply'])

class SimpleSolver:
    '''Main class that represents the graph'''

    def __init__(
            self,
            num_reviews,
            demands,
            cost_matrix,
            constraint_matrix,
            logger=logging.getLogger(__name__),
            strict=True,
        ):

        self.logger = logger

        self.cost = 0
        self.solved = False
        self.cost_matrix = cost_matrix
        self.constraint_matrix = constraint_matrix
        self.flow_matrix = np.zeros(np.shape(self.cost_matrix))
        self.num_reviews = num_reviews
        self.demands = demands
        self.num_papers = np.size(cost_matrix, axis=0)
        self.num_reviewers = np.size(cost_matrix, axis=1)
        self.current_offset = 0

        self._check_inputs(strict)

        self.start_nodes = []
        self.end_nodes = []
        self.capacities = []
        self.costs = []
        self.node_by_number = {}

        total_supply = min(sum(self.num_reviews), sum(self.demands))


        # -- Add Nodes --

        # no index because the source isn't represented in the cost/constraint matrices.
        self.source_node = self.add_node(
            index=None,
            supply=total_supply)

        self.reviewer_nodes = [self.add_node(i) for i in range(self.num_reviewers)]
        self.paper_nodes = [self.add_node(i) for i in range(self.num_papers)]

        # no index because the sink isn't represented in the cost/constraint matrices.
        self.sink_node = self.add_node(index=None, supply=(-1 * total_supply))

        # make various indexes for Nodes
        self.reviewer_node_by_index = {n.index: n for n in self.reviewer_nodes}
        self.paper_node_by_index = {n.index: n for n in self.paper_nodes}


        # -- Add Edges --

        # connect the source node to all reviewer nodes.
        for r_node in self.reviewer_nodes:
            capacity = self.num_reviews[r_node.index]
            self.add_edge(self.source_node, r_node, capacity, cost=0)

        for r_node in self.reviewer_nodes:
            for p_node in self.paper_nodes:

                coordinates = (p_node.index, r_node.index)
                arc_cost = int(self.cost_matrix[coordinates])
                arc_constraint = self.constraint_matrix[coordinates]

                # arc_constraint of 0 means there's no constraint;
                # apply the cost as normal.
                if arc_constraint == 0:
                    self.add_edge(r_node, p_node, 1, arc_cost)

                # arc_constraint of 1 means that this user was explicitly assigned to this paper
                # TODO: this should be handled as a hard constraint
                if arc_constraint == 1:
                    arc_cost = self._least_cost() - 1
                    self.add_edge(r_node, p_node, 1, int(arc_cost))

        # connect paper nodes to the sink node.
        for p_node in self.paper_nodes:
            capacity = self.demands[p_node.index]
            self.add_edge(p_node, self.sink_node, capacity, cost=0)

        self.construct_solver()

    def _check_inputs(self, strict):
        '''Validate inputs (e.g. that matrix and array dimensions are correct)'''
        self.logger.debug('Checking graph inputs')

        num_papers = np.size(self.cost_matrix, axis=0)
        num_reviewers = np.size(self.cost_matrix, axis=1)

        for matrix in [self.cost_matrix, self.constraint_matrix]:
            if not isinstance(matrix, np.ndarray):
                raise SolverException(
                    'cost and constraint matrices must be of type numpy.ndarray')

        if not np.shape(self.cost_matrix) == np.shape(self.constraint_matrix):
            raise SolverException(
                'cost {} and constraint {} matrices must be the same shape'.format(
                    np.shape(self.cost_matrix), np.shape(self.constraint_matrix)))

        if not len(self.num_reviews) == num_reviewers:
            raise SolverException(
                'num_reviews must be same length ({}) as number of reviewers ({})'.format(
                    len(self.num_reviews), num_reviewers))

        if not len(self.demands) == num_papers:
            raise SolverException(
                'self.demands array must be same length ({}) as number of papers ({})'.format(
                    len(self.demands), num_papers))

        supply = sum(self.num_reviews)
        demand = sum(self.demands)
        if strict and supply < demand:
            raise SolverException(
                'total supply of reviews ({}) must be greater than total demand ({})'.format(
                    supply, demand))

    def _check_graph_integrity(self):
        '''Ensure that graph arrays are well-formed for use by OR-Tools.'''
        self.logger.debug('Checking graph integrity')

        equal_lengths = len(self.start_nodes) \
            == len(self.end_nodes) \
            == len(self.capacities) \
            == len(self.costs)

        if not equal_lengths:
            raise SolverException(
                '''start_nodes({}), end_nodes({}), capacities({}), and costs({})
                must all be equal'''.format(
                    len(self.start_nodes),
                    len(self.end_nodes),
                    len(self.capacities),
                    len(self.costs)))

        if any([not isinstance(i, int) for i in self.capacities]):
            raise SolverException(
                'capacities list may not contain integers of type numpy.int64')

        if any([not isinstance(i, int) for i in self.costs]):
            raise SolverException(
                'costs list may not contain integers of type numpy.int64')


    def _boundary_cost(self, boundary_function):
        '''
        A helper function used by _greatest_cost and _least_cost.

        '''
        if self.cost_matrix.shape > (0, 0):
            cost_boundary = self.cost_matrix[
                np.unravel_index(boundary_function(), self.cost_matrix.shape)]
            return cost_boundary

        return None

    def _greatest_cost(self):
        '''
        finds the greatest value in cost_matrix.

        '''
        return self._boundary_cost(self.cost_matrix.argmax)

    def _least_cost(self):
        '''
        finds the lowest value in cost_matrix.

        '''
        return self._boundary_cost(self.cost_matrix.argmin)

    def add_node(self, index, supply=0):
        '''
        Register a new, unconnected Node object with this graph, with the given index and supply.
        Assigns the Node the next available number, given all other Nodes in the graph.

        '''

        # cast `supply` to Python int because SimpleMinCostFlow can't handle other int types
        # (e.g. numpy.int64)
        new_node = Node(number=self.current_offset, index=index, supply=int(supply))

        if new_node.number in self.node_by_number:
            raise SolverException(
                'Node {} already exists in assignment graph.'.format(new_node.number))
        else:
            self.node_by_number[new_node.number] = new_node
            self.current_offset += 1
            return new_node

    def add_edge(self, start_node, end_node, capacity, cost):
        '''
        Adds an "edge" between `start_node` and `end_node` with the given capacity and cost.

        Edges are represented virtually by the presence of Node numbers in the aligned arrays
        `self.start_nodes` and `self.end_nodes`; there is no "Edge" object.
        '''

        self.start_nodes.append(start_node)
        self.end_nodes.append(end_node)

        # cast `capacity` to Python int because SimpleMinCostFlow can't handle other int types
        # (e.g. numpy.int64)
        self.capacities.append(int(capacity))
        self.costs.append(cost)

    def construct_solver(self):
        '''
        Constructs the OR-Tools MinCostFlow solver with this SimpleSolver's Nodes and edges.
        '''
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
        '''
        Executes the OR-Tools MinCostFlow solver,
        and returns the solution in the form of a flow matrix.

        '''
        assert hasattr(self, 'min_cost_flow'), \
            'Solver not constructed. Run self.construct_solver() first.'
        self.cost = 0
        if self.min_cost_flow.Solve() == self.min_cost_flow.OPTIMAL:
            self.solved = True
            for i in range(self.min_cost_flow.NumArcs()):
                self.cost += self.min_cost_flow.Flow(i) * self.min_cost_flow.UnitCost(i)
                r_node = self.node_by_number[self.min_cost_flow.Tail(i)]
                p_node = self.node_by_number[self.min_cost_flow.Head(i)]
                flow = self.min_cost_flow.Flow(i)

                if r_node in self.reviewer_nodes and p_node in self.paper_nodes:
                    self.flow_matrix[p_node.index, r_node.index] = flow
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
