import numpy as np
from openreview_matcher.evals import base_evaluator
from openreview_matcher import utils

class Evaluator(base_evaluator.Evaluator):
    """
    An Evaluator instance that evaluates
    mean_avg_precision =
        (number of papers reviewers bid positively on in top M) /
        (total number of papers retrieved)

    This evaluation method requires us to look at the bids, so we import 
    them from somewhere in the __init__() method
    """

    def __init__(self, params=None):
        data_path = params["data_path"]
        self.data = utils.load_obj(data_path)
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

        scores_by_forum = {}
        for forum, rank_list in ranklists:
            positive_labels = ["I want to review", "I can review"]
            positive_bids = [bid.signatures[0].encode('utf-8') for bid in self.bids_by_forum[forum] if bid.tag in positive_labels]
            relevant_reviewers = [1 if reviewer_id in positive_bids else 0 for reviewer_id in rank_list]
            avg_precision = self.average_precision(relevant_reviewers)
            yield forum, [avg_precision]

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

    def average_precision(self, ranked_list):
        """ 
        Computes the average precision over a ranked list
        The average precision is the just precision at every relevant rank

        Arguments:
            ranked_list: a ranked list of reviewers
        """

        avg_precision = [self.precision_at_m(ranked_list, m+1) for m in range(len(ranked_list)) if ranked_list[m]]
        if not avg_precision:
            return 0
        else:
            return np.mean(avg_precision)
