import re

from collections import defaultdict

import numpy as np
from openreview_matcher import utils
from openreview_matcher import metadata
from openreview_matcher.models import base_model

class Model(base_model.Model):
    def __init__(self,params=None):
        self.reviewers = set()

    def fit(self, train_data, archive_data):
        self.reviewers = set([record['reviewer_id'] for record in archive_data])

    def predict(self, note_record):
        scores = [(signature, self.score(signature, note_record['forum'])) for signature in self.reviewers]
        return [signature for signature, score in sorted(scores, key=lambda x: x[1], reverse=True)]

    def score(self, signature, forum):
        return np.random.random()


