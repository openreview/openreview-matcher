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
        """ Return a graph of precision vs m """

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

    def evaluate_using_individual_queries(self, ranklists):
        """ Evaluate using individual query ranks """

        all_precision_values = []
        for forum, rank_list in ranklists:
            rank_list = [rank.split(";")[0] for rank in rank_list]
            scores = []
            for m, reviewer in enumerate(rank_list, start=1):
                positive_labels = ["I want to review", "I can review"]
                positive_bids = [bid["signature"] for bid in self.get_pos_bids_for_forum(forum)]
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

    def get_all_bids_for_forum(self, forum_id):
        """ Returns all bids for the forum_id """
        bids_by_forum_id = self.eval_data[forum_id]
        return [{"signature": bid.signatures[0], "bid": bid.tag} for bid in bids_by_forum_id]

    def get_pos_bids_for_forum(self, forum_id):
        """ Get all of the positive bids for a forum """
        positive_labels = ["I want to review", "I can review"]
        forum_bids = self.get_all_bids_for_forum(forum_id)
        return [bid for bid in forum_bids if bid["bid"] in positive_labels]

