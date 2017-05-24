import re

from collections import defaultdict

import numpy as np
from openreview_matcher import utils
from openreview_matcher.models import base_model

class Model(base_model.Model):
    def __init__(self,params=None):
        self.reviewers = set()

    def fit(self, train_data, archive_data):
        for record in archive_data:
            if 'reviewer_id' in record:
                self.reviewers.update([record['reviewer_id']])

    def predict(self, test_papers):
        rank_list = np.random.permutation(list(self.reviewers))
        return rank_list

