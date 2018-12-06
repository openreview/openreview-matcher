#!/usr/bin/python
# -*- coding: utf-8 -*-

# sums list of numbers and omits things like 'inf' and '-inf'
def safe_sum(lst):
    sum = 0
    for n in lst:
        if type(n) == float:
            sum += n
    return sum


def weight_scores(scores, weights):
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
            weighted_scores[feature] = scores[feature] * weights[feature]

    return weighted_scores


def cost(scores, weights, precision=0.01):
    weighted_scores = weight_scores(scores, weights)
    score_sum = safe_sum(weighted_scores.values())
    return -1 * int(score_sum / precision)

