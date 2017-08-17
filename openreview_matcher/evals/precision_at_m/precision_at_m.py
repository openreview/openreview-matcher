from operator import itemgetter

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

from openreview_matcher.evals import base_evaluator
from openreview_matcher import utils

matplotlib.style.use('ggplot')


class Evaluator(base_evaluator.Evaluator):
    """
    An Evaluator instance that evaluates
    precision_at_m =
        (number of papers reviewers bid positively on in top M) /
        (total number of papers retrieved)

    This evaluation method requires us to look at the bids, so we import 
    them from somewhere in the __init__() method
    """

    def __init__(self, eval_data, params=None):
        self.eval_data = eval_data 
        self.m_values = params["m_values"]

    def evaluate(self, ranklists):
        """
        Evaluate the model using a ranked list. Either you can evaluate using a single ranked list or 
        evaluate against each individual query and average their precision scores
        
        Arguments
            @ranklists: a list of tuples.
            The 0th index of the tuple contains the forum ID of the rank of the list being evaluated
            The 1st index of the tuple contains a list of reviewer IDS, in order of expertise score

        Returns
            a generator object that yields an array of scores for each ranked list. If only one score
            is need, return the score in an array by itself

        """

        # return self.evaluate_using_single_rank(ranklists)
        return self.evaluate_using_individual_queries(ranklists)


    def evaluate_using_individual_queries(self, ranklists):
        """ Evaluate using individual query ranks """

        for forum, rank_list in ranklists:
            rank_list = [rank.split(";")[0] for rank in rank_list]
            scores = []
            for m in self.m_values:
                positive_labels = ["I want to review", "I can review"]
                positive_bids = [bid["signature"] for bid in self.eval_data.get_pos_bids_for_forum(forum)]
                relevant_reviewers = [1 if reviewer_id in positive_bids else 0 for reviewer_id in rank_list]
                precision = self.precision_at_m(relevant_reviewers, m)
                scores.append(precision)
            yield forum, scores

    def setup_ranked_list(self, rank_list):
        """
        Setup the single ranked list for a model 
        Combines all of the individual query ranks into one single rank 
        
        """
        
        new_rank_list = []

        for forum, rank_list in rank_list:
            for reviewer_score in rank_list:
                reviewer = reviewer_score.split(";")[0]
                score = float(reviewer_score.split(";")[1])
                has_bid = self.eval_data.reviewer_has_bid(reviewer, forum)  # filter for reviewers that gave a bid value
                if has_bid:
                    new_rank_list.append((reviewer, score, forum))
        ranked_reviewers = sorted(new_rank_list, key=itemgetter(1), reverse=True)
        return ranked_reviewers


    def evaluate_using_single_rank(self, rank_list):
        """
        Evaluate against a single ranked list computed by the model  
        """

        ranked_reviewers = self.setup_ranked_list(rank_list)

        scores = []

        positive_bids = 0
        for reviewer, score, forum in ranked_reviewers:
            bid = self.eval_data.get_bid_for_reviewer_paper(reviewer, forum)
            if bid == 1:
                positive_bids +=1

        for m in range(1, len(ranked_reviewers) + 1):
            topM = ranked_reviewers[0: m]
            topM = map(lambda reviewer: (reviewer[0], self.eval_data.get_bid_for_reviewer_paper(reviewer[0], reviewer[2])), topM)
            pos_bids_from_topM = [bid for bid in topM if bid[1] == 1]
            precision = float(len(pos_bids_from_topM)) / float(m)  # precision => relevant bids retrieved / # of retrieved
            scores.append((m, precision))

        return scores

    def precision_at_m(self, ranked_list, m):
        """ 
        Computes precision at M 
        
        Arguments:
            ranked_list: ranked list of reviewers for a forum where each entry is either a 0 or 1
                        1 -  reviewer that reviewer wanted to bid 
                        0 - reviewer did not want to bid

            m: cuttoff value
        Returns:
            A float representing the precision
        """

        topM = np.asarray(ranked_list)[:m] != 0
        return np.mean(topM)
