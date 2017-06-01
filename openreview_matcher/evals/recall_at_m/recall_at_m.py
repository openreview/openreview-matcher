import sys, os
import argparse

from collections import defaultdict

from openreview_matcher.evals import base_evaluator
from openreview_matcher import utils


class Evaluator(base_evaluator.Evaluator):
    """
    An Evaluator instance that evaluates
    recall_at_m =
        (number of papers reviewer bid positively on in top M) /
        (total number of papers reviewer bid positively on)

    This evaluation method requires us to look at the bids, so we import them
    from somewhere in the __init__() method.

    """

    def __init__(self, params=None):

        datapath = os.path.join(os.path.dirname(__file__), '../samples/uai_data')

        self.data = utils.load_obj(datapath)
        self.bids_by_forum = self.data['bids_by_forum']


    def evaluate(self, ranklists):
        """
        Arguments
            @ranklists: A list of tuples.
            The 0th index of the tuple contains the forum ID of the rank list being evaluated.
            The 1st index of the tuple contains a list of reviewer IDs, in order of expertise score.

        Returns
            a generator object that yields an array of scores for each ranked list. If only one
            score is needed, return the score in an array by itself.
        """

        scores_by_forum = {}
        for forum, rank_list in ranklists:

            scores = []

            for m in [5, 20, 35, 50]:
                topM = rank_list[0: m]
                positive_labels = ['I want to review','I can review']
                positive_bids = [bid for bid in self.bids_by_forum[forum] if bid.tag in positive_labels]
                pos_bids_from_topM = [bid for bid in positive_bids if bid.signatures[0].encode('utf-8') in topM]

                if float(len(positive_bids)) > 0:
                    scores.append(float(len(pos_bids_from_topM))/float(len(positive_bids)))
                else:
                    scores.append(0.0)
            """
            You can replace the code above with a new evaluation method
            """

            yield forum, scores
