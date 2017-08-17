import os
from operator import itemgetter
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from openreview_matcher.graphing import base_graphing
from openreview_matcher import utils
import numpy as np

matplotlib.style.use('ggplot')

class Graphing(base_graphing.Graphing):
    """ Graphing precision vs m """
    def __init__(self, eval_data, params=None):
        self.eval_data = eval_data

    def graph(self, ranklists, ax, model_name):
        # precision_values = self.evalutate_precision(ranklists)
        precision_values = self.evaluate_using_individual_queries(ranklists)

        df_precision = pd.DataFrame({
            '@M': range(1, len(precision_values) + 1),
            model_name: precision_values
        })

        ax = df_precision.plot.line(x="@M", y=model_name, ax=ax)
        ax.set_title("Precision vs M", y=1.08)
        ax.set_ylabel("Precision")
        ax.set_xlabel("@M")
        return ax

    def setup_ranked_list(self, ranklists):
        """
        Setup the single ranked list for a model
        Combines all of the individual query ranks into one single rank
        """
        new_rank_list = []

        for forum, rank_list in ranklists:
            for reviewer_score in rank_list:
                reviewer = reviewer_score.split(";")[0]
                score = float(reviewer_score.split(";")[1])
                # filter for reviewers that gave a bid value
                has_bid = self.eval_data.reviewer_has_bid(reviewer, forum)
                if has_bid:
                    new_rank_list.append((reviewer, score, forum))
        ranked_reviewers = sorted(
            new_rank_list, key=itemgetter(1), reverse=True)
        return ranked_reviewers

    def evaluate_using_individual_queries(self, ranklists):
        """ Evaluate using individual query ranks """

        all_precision_values = []
        for forum, rank_list in ranklists:
            rank_list = [rank.split(";")[0] for rank in rank_list]
            scores = []
            for m, reviewer in enumerate(rank_list, start=1):
                positive_labels = ["I want to review", "I can review"]
                positive_bids = [bid["signature"] for bid in self.eval_data.get_pos_bids_for_forum(forum)]
                relevant_reviewers = [1 if reviewer_id in positive_bids else 0 for reviewer_id in rank_list]
                precision = self.precision_at_m(relevant_reviewers, m)
                scores.append(precision)
            all_precision_values.append(scores)

        return np.mean(all_precision_values, axis=0)

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

    def evalutate_precision(self, rank_list):
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
            scores.append(precision)

        return scores 
