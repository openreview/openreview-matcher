import re

from collections import defaultdict

from models import base_model

import numpy as np
from util import utils

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

