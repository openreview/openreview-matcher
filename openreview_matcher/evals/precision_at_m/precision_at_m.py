import sys, os
import argparse
import numpy as np
from collections import defaultdict

from openreview_matcher.evals import base_evaluator
from openreview_matcher import utils

class Evaluator(base_evaluator.Evaluator):
    """
    An Evaluator instance that evaluates
    precision_at_m =
        (number of papers reviewers bid positively on in top M) /
        (total number of papers retrieved)

    This evaluation method requires us to look at the bids, so we import 
    them from somewhere in the __init__() method
    """

    def __init__(self, params=None):
        datapath = params["data_path"]
        self.m_values = params["m_values"]
        self.data = utils.load_obj(datapath)
        self.bids_by_forum = self.data["bids_by_forum"]

    def evaluate(self, ranklists):
        """
        Arguments
            @ranklists: a list of tuples.
            The 0th index of the tuple contains the forum ID of the rank of the list being evaluated
            The 1st index of the tuple contains a list of reviewer IDS, in order of expertise score

        Returns
            a generator object that yields an array of scores for each ranked list. If only one score
            is need, return the score in an array by itself

        """

        for forum, rank_list in ranklists:
            scores = []
            for m in self.m_values:
                positive_labels = ["I want to review", "I can review"]
                positive_bids = [bid.signatures[0].encode('utf-8') for bid in self.bids_by_forum[forum] if bid.tag in positive_labels]
                relevant_reviewers = [1 if reviewer_id in positive_bids else 0 for reviewer_id in rank_list] 
                precision = self.precision_at_m(relevant_reviewers, m)
                scores.append(precision)
            yield forum, scores

    def precision_at_m(self, ranked_list, m):
        """ 
        Computes precision at M 
        
        Arguments:
            ranked_list: ranked list of reviewers for a forum
            m: cuttoff value
        Returns:
            A float representing the precision
        """

        topM = np.asarray(ranked_list)[:m] != 0
        return np.mean(topM)
