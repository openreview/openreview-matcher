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

    def __init__(self, supplies, demands, cost_matrix, constraint_matrix):

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
        # self.solution = np.zeros((self.num_reviewers, self.num_papers + 1))

        # finds the largest and smallest value in cost_matrix
        # (i.e. the greatest and lowest cost of any arc)
        self.max_cost = self.cost_matrix[
            np.unravel_index(self.cost_matrix.argmax(), self.cost_matrix.shape)]
        self.min_cost = self.cost_matrix[
            np.unravel_index(self.cost_matrix.argmin(), self.cost_matrix.shape)]

        # supplies array must be same length as number of reviewers
        assert len(supplies) == self.num_reviewers, \
            'The length of the supplies array ({}) \
            must equal np.size(cost_matrix, axis=0) ({})'''.format(
            len(supplies), self.num_reviewers
        )
        self.supplies = supplies

        # demands array must be same length as number of papers
        assert len(demands) == self.num_papers, \
            'The length of the demands array ({}) \
            must equal np.size(cost_matrix, axis=0) ({})'.format(
            len(demands), self.num_papers)

        self.demands = [-1 * c for c in demands]

        # the total supply of reviews must be greater than the total demand
        net_supply = sum(self.supplies) + sum(self.demands)
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

        self.reviewer_nodes = [Node(
            number = i,
            index = i,
            supply = self.supplies[i]) for i in range(self.num_reviewers)]

        self.paper_nodes = [Node(
            number = i + self.num_reviewers,
            index = i,
            supply = self.demands[i]) for i in range(self.num_papers)]

        # overflow node has no index because it is not represented in the cost
        # or constraint matrices
        self.overflow_node = Node(
            number = self.num_reviewers + self.num_papers,
            index = None,
            supply = -1 * net_supply)

        self.node_by_number = { n.number: n for n in \
            self.reviewer_nodes + self.paper_nodes + [self.overflow_node] }

        # set up the arcs
        self.start_nodes = []
        self.end_nodes = []
        self.capacities = []
        self.costs = []

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

                    if arc_constraint == 0:
                        self.costs.append(int(arc_cost))

                    if arc_constraint == 1:
                        self.costs.append(int(self.min_cost - 1))

            self.start_nodes.append(r_node)
            self.end_nodes.append(self.overflow_node)
            self.capacities.append(sum(self.supplies))
            self.costs.append(int(self.max_cost + 1))

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
                r_node = self.node_by_number[self.min_cost_flow.Tail(i)]
                p_node = self.node_by_number[self.min_cost_flow.Head(i)]
                flow = self.min_cost_flow.Flow(i)

                if p_node.index == None:
                    # the overflow node has no index because it is not
                    # represented in the cost/constraint matrices
                    self.overflow[r_node.index] = flow
                else:
                    self.flow_matrix[r_node.index, p_node.index] = flow

            return np.concatenate([self.flow_matrix, self.overflow], axis=1)
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
