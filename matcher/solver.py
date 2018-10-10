from __future__ import print_function, division
from ortools.graph import pywrapgraph
from collections import namedtuple
import numpy as np

def decode_cost_matrix(solution, user_by_index, forum_by_index):
    '''
    Decodes the 2D score matrix into a returned dict of user IDs keyed by forum ID.

    e.g. {
        'abcXYZ': '~Melisa_Bok1',
        '123-AZ': '~Michael_Spector1'
    }
    '''

    assignments_by_forum = defaultdict(list)
    for var_name in solution:
        var_val = var_name.split('x_')[1].split(',')

        user_index, paper_index = (int(var_val[0]), int(var_val[1]))
        user_id = user_by_index[user_index]
        forum = forum_by_index[paper_index]
        match = solution[var_name]

        if match == 1:
            assignments_by_forum[forum].append(user_id)

    return assignments_by_forum

class Solver(object):

    '''

    '''

    def __init__(self, minimums, maximums, demands, cost_matrix, constraint_matrix):

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

        self.overflow = np.zeros((self.num_reviewers, 1))

        # finds the largest and smallest value in cost_matrix
        # (i.e. the greatest and lowest cost of any arc)
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

        # the total supply of reviews must be greater than the total demand
        net_supply = sum(self.maximums) + sum(self.demands)
        assert net_supply >= 0, \
            'demand exceeds supply (net supply: {})'.format(net_supply)

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

        self.reviewer_node_by_number = {n.number:n for n in self.reviewer_nodes}
        self.paper_node_by_number = {n.number:n for n in self.paper_nodes}

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
                self.maximums[free_node.index] - self.minimums[free_node.index])

            # TODO: Is this the right way to set the cost of the overflow?
            self.costs.append(int(self.max_cost + 1))

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

        # construct the solver, adding nodes and arcs
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

        self.solved = False

    def solve(self):
        if self.min_cost_flow.Solve() == self.min_cost_flow.OPTIMAL:
            self.solved = True
            for i in range(self.min_cost_flow.NumArcs()):
                cost = self.min_cost_flow.Flow(i) * self.min_cost_flow.UnitCost(i)
                r_node = self.reviewer_node_by_number.get(self.min_cost_flow.Tail(i))
                p_node = self.paper_node_by_number.get(self.min_cost_flow.Head(i))
                flow = self.min_cost_flow.Flow(i)

                if r_node and p_node:
                    self.flow_matrix[r_node.index, p_node.index] = flow

            return self.flow_matrix
        else:
            print('There was an issue with the min cost flow input.')
            return None

if __name__ == '__main__':
    cost_matrix = np.array([
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
        [2, 2, 1]
    ])

    solver = Solver([1,1,1,1], [1,1,2], cost_matrix)
    solver.solve()

    print('Minimum cost:', solver.min_cost_flow.OptimalCost())
    print('')
    print('  Arc    Flow / Capacity  Cost')
    for i in range(solver.min_cost_flow.NumArcs()):
        cost = solver.min_cost_flow.Flow(i) * solver.min_cost_flow.UnitCost(i)
        print('%1s -> %1s   %3s  / %3s       %3s' % (
          solver.min_cost_flow.Tail(i),
          solver.min_cost_flow.Head(i),
          solver.min_cost_flow.Flow(i),
          solver.min_cost_flow.Capacity(i),
          cost))
