#!/usr/bin/python
# -*- coding: utf-8 -*-

class CostFunction:

    def __init__ (self, precision=0.01):
        self.precision = precision

    # sums list of numbers and omits things like 'inf' and '-inf'
    def safe_sum(self, lst):
        sum = 0
        for n in lst:
            if type(n) == float:
                sum += n
        return sum


    def weight_scores(self, scores, weights):
        '''
        scores: a dict of scores keyed on score name

        weights: a dict of weights keyed on score name

        returns a dict of weighted scores, keyed on score names found in @weights
        (i.e. result ignores values in @scores that are not present in @weights)

        Example:

        >>> weight_scores({'tpms': 0.5, 'bid': 1.0 }, { 'tpms': 1.5 })
        {'tpms': 0.75}

        '''
        weighted_scores = {}
        for feature in weights:
            if feature in scores:
                weighted_scores[feature] = float(scores[feature]) * weights[feature]

        return weighted_scores

    def aggregate_score (self, scores, weights):
        weighted_scores = self.weight_scores(scores, weights)
        return self.safe_sum(weighted_scores.values())

    def cost(self, scores, weights):
        '''
        compute the weighted average of the scores and return it an enlarged negative float so it serves as a cost (for use in a minimization algorithm)
        :param scores: a dict like {'tpms': 0.49, 'recommendation': 0.75}
        :param weights: a dict like {'tpms': 1, 'recommendation': 2}
        :return:
        '''
        val = -1 * self.aggregate_score(scores, weights) / self.precision
        if val == -0.0:
            return 0.0
        else:
            return val



