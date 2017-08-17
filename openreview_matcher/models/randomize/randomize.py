import re

from collections import defaultdict

import numpy as np
from openreview_matcher import utils
from openreview_matcher.models import base_model

class Model(base_model.Model):

	def __init__(self, combinining_mechanism, scoring_mechanism, keyphrase_extractor, params=None):
		self.reviewers = set()

   	def fit(self, train_data, archive_data):
        self.reviewers = set([record['signature'] for record in archive_data])

    def predict(self, note_record):
        scores = [(signature, self.score(signature, note_record['forum'])) for signature in self.reviewers]
        sorted_scores = [(signature, score) for signature, score in sorted(scores, key=lambda x: x[1], reverse=True)]
        ranked_reviewer_list = ["{0};{1}".format(reviewer_scores[0].encode('utf-8'),reviewer_scores[1]) for
                                reviewer_scores in sorted_scores]

        return ranked_reviewer_list


    def score(self, signature, note_record):
        return np.random.random()


