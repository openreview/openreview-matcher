import os

from operator import itemgetter
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from openreview_matcher.evals import base_evaluator
from openreview_matcher import utils

matplotlib.style.use('ggplot')


class Evaluator(base_evaluator.Evaluator):
    """
    An Evaluator instance that evaluates
    recall_at_m =
        (number of papers reviewer bid positively on in top M) /
        (total number of papers reviewer bid positively on)

    This evaluation method requires us to look at the bids, so we import them
    from somewhere in the __init__() method.

    """

    def __init__(self, eval_data, params=None):
        self.eval_data = eval_data
        self.m_values = params["m_values"]

    def evaluate(self, ranklists):
        """
        Evaluate the model using a ranked list. Either you can evaluate using a single ranked list or
        evaluate against each individual query and average their precision scores
        
        Arguments
            @ranklists: A list of tuples.
            The 0th index of the tuple contains the forum ID of the rank list being evaluated.
            The 1st index of the tuple contains a list of reviewer IDs, in order of expertise score.

        Returns
            a generator object that yields an array of scores for each ranked list. If only one
            score is needed, return the score in an array by itself.
        """
        # return self.evaluate_using_single_rank(ranklists)
        return self.evaluate_using_individual_queries(ranklists)

    def evaluate_using_individual_queries(self, ranklists):
        """ Evaluate using individual query ranks"""
        for forum, rank_list in ranklists:
            rank_list = [rank.split(";")[0] for rank in rank_list]
            scores = []
            for m in self.m_values:
                topM = rank_list[:m]
                positive_labels = ['I want to review', 'I can review']
                positive_bids = self.eval_data.get_pos_bids_for_forum(forum)
                pos_bids_from_topM = [bid for bid in positive_bids if bid["signature"] in topM]
                if float(len(positive_bids)) > 0:
                    scores.append(float(len(pos_bids_from_topM))/float(len(positive_bids)))
                else:
                    scores.append(0.0)
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
                has_bid = self.reviewer_has_bid(reviewer, forum)  # filter for reviewers that gave a bid value
                if has_bid:
                    new_rank_list.append((reviewer, score, forum)) 
        ranked_reviewers = sorted(new_rank_list, key=itemgetter(1), reverse=True)
        return ranked_reviewers

    def reviewer_has_bid(self, reviewer, paper):
        """ Returns True if the reviewer bid on that 'paper' """
        paper_bids = self.bids_by_forum[paper]
        has_bid = [True if bid.signatures[0] == reviewer.decode("utf-8") else False for bid in paper_bids][0]
        return has_bid

    def get_bid_for_reviewer_paper(self, reviewer, paper):
        """ 
        Gets the bid for the reviewer and the paper 
        Returns 0 if the bid is not relevant and 1 if the bid is relevant
        """
        positive_labels = ['I want to review','I can review']
        paper_bids = self.bids_by_forum[paper]
        bid_value = [1 if bid.tag in positive_labels else 0 for bid in paper_bids if bid.signatures[0] == reviewer.decode('utf-8')]
        if len(bid_value) > 0:
            return bid_value[0]
        else:
            return 0

    def evaluate_using_single_rank(self, rank_list):
        """ Evaluate against a single ranked list computed by the model """

        ranked_reviewers = self.setup_ranked_list(rank_list)

        scores = []

        positive_bids = 0
        for reviewer, score, forum in ranked_reviewers:
            bid = self.get_bid_for_reviewer_paper(reviewer, forum)
            if bid == 1:
                positive_bids +=1

        for m in range(1, len(ranked_reviewers) + 1):
            topM = ranked_reviewers[0: m]
            topM = map(lambda reviewer: (reviewer[0], self.get_bid_for_reviewer_paper(reviewer[0], reviewer[2])), topM)
            pos_bids_from_topM = [bid for bid in topM if bid[1] == 1]

            if float(positive_bids) > 0:
                scores.append((m, float(len(pos_bids_from_topM))/float(positive_bids)))
            else:
                scores.append((m, 0.0))
        return scores
