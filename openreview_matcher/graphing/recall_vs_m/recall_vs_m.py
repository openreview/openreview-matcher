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
    """ Graphing recall vs m """
    def __init__(self, eval_data, params=None):
        self.eval_data = eval_data

    def graph(self, ranklists, ax, model_name):
        """ Return a graph of recall vs m """ 
        recall_values = self.evaluate_against_individual_queries(ranklists)

        print("Recall Values to Graph: ", recall_values)
        df_recall = pd.DataFrame({
            '@M': range(1, len(recall_values) + 1),
            model_name: recall_values
        })

        ax = df_recall.plot.line(x="@M", y=model_name, ax=ax)
        ax.set_title("Recall vs M", y=1.08)
        ax.set_ylabel("Recall")
        ax.set_xlabel("@M")
        return ax

    def evaluate_against_individual_queries(self, ranklists):
        """ Evaluate using individual query ranks"""

        recall_scores = []

        for forum, rank_list in ranklists:
            rank_list = [rank.split(";")[0] for rank in rank_list]
            scores = []
            for m, reviewer in enumerate(rank_list, start=1):
                topM = rank_list[:m]
                positive_labels = ['I want to review', 'I can review']
                positive_bids = self.get_pos_bids_for_forum(forum)
                pos_bids_from_topM = [bid for bid in positive_bids if bid["signature"] in topM]
                if float(len(positive_bids)) > 0:
                    scores.append(float(len(pos_bids_from_topM))/float(len(positive_bids)))
                else:
                    scores.append(0.0)
            recall_scores.append(scores)
        return np.mean(recall_scores, axis=0)

    def get_all_bids_for_forum(self, forum_id):
        """ Returns all bids for the forum_id """
        bids_by_forum_id = self.eval_data[forum_id]
        return [{"signature": bid.signatures[0], "bid": bid.tag} for bid in bids_by_forum_id]

    def get_pos_bids_for_forum(self, forum_id):
        """ Get all of the positive bids for a forum """
        positive_labels = ["I want to review", "I can review"]
        forum_bids = self.get_all_bids_for_forum(forum_id)
        return [bid for bid in forum_bids if bid["bid"] in positive_labels]
