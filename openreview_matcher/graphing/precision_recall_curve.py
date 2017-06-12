""" Graphs the precision and recall curve for a model's ranked output """

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

from openreview_matcher import utils

matplotlib.style.use('ggplot')


datapath = "openreview_matcher/evals/samples/uai_data"
data = utils.load_obj(datapath)
bids_by_forum = data["bids_by_forum"]


def precision_recall_curve(ranked_list):
    """ 
        Return a matplotlib figure of precision/recall curve
    """

    precision_for_model = []
    recall_for_model = []
    for forum, rank_list in ranked_list:
        precisions_for_forum = []
        recalls_for_forum = []
        for m in range(len(rank_list)):
            positive_labels = ["I want to review", "I can review"]
            positive_bids = [bid.signatures[0].encode('utf-8') for bid in bids_by_forum[forum] if
                             bid.tag in positive_labels]
            relevant_reviewers = [1 if reviewer_id in positive_bids else 0 for reviewer_id in rank_list]
            precision = precision_at_m(relevant_reviewers, m)
            recall = recall_at_m(m, relevant_reviewers)
            precisions_for_forum.append(precision)
            recalls_for_forum.append(recall)
        precision_for_model.append(precisions_for_forum)
        recall_for_model.append(recalls_for_forum)

    print("Precision for model: ", precision_for_model)
    print("Recall for model: ", recall_for_model)


def precision_at_m(ranked_list, m):
    """ 
    Computes precision at M 
    """

    topM = np.asarray(ranked_list)[:m] != 0
    return np.mean(topM)


def recall_at_m(m, rank_list):
    """ Implementation of recall at m """

    topM = np.asarray(rank_list)[:m] != 0
    pos_bids_from_topM = len(topM)
    if float(len(rank_list)) > 0:
        return float(pos_bids_from_topM) / float(sum(rank_list))
    else:
        return 0.0

