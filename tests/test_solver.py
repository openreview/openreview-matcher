import numpy as np
import unittest
from matcher.solver import Solver


class TestFlaskApi(unittest.TestCase):

    def test_solver (self):
        cost_matrix = np.array([
            [0, 1, 1],
            [1, 0, 1],
            [1, 1, 0],
            [2, 2, 1]
        ])
        constraint_matrix = np.zeros(np.shape(cost_matrix))
        solver = Solver([1,1,1,1], [2,2,2,2], [1,1,2], cost_matrix, constraint_matrix)
        res = solver.solve()
        assert res.shape == (4,3)
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
            if solver.min_cost_flow.Tail(i) == 12 and solver.min_cost_flow.Head(i) == 15:
                assert cost == 1
            else:
                assert cost == 0
