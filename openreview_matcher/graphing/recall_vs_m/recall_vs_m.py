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
        # recall_values = self.evaluate_recall(ranklists)
        recall_values = self.evaluate_using_individual_queries(ranklists)

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
        """ Evaluate using individual query ranks"""

        recall_scores = []

        for forum, rank_list in ranklists:
            rank_list = [rank.split(";")[0] for rank in rank_list]
            scores = []
            for m, reviewer in enumerate(rank_list, start=1):
                topM = rank_list[:m]
                positive_labels = ['I want to review', 'I can review']
                positive_bids = self.eval_data.get_pos_bids_for_forum(forum)
                pos_bids_from_topM = [bid for bid in positive_bids if bid["signature"] in topM]
                if float(len(positive_bids)) > 0:
                    scores.append(float(len(pos_bids_from_topM))/float(len(positive_bids)))
                else:
                    scores.append(0.0)
            recall_scores.append(scores)
        return np.mean(recall_scores, axis=0)

    def evaluate_recall(self, rank_list):
        """ Evaluate against a single ranked list computed by the model """

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

            if float(positive_bids) > 0:
                scores.append(float(len(pos_bids_from_topM))/float(positive_bids))
            else:
                scores.append(0.0)
        return scores
