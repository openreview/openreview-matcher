from openreview_matcher.models import base_model


class Model(base_model.Model):
    def __init__(self, params=None):
        pass
    def fit(self, train_data, archive_data):
        pass
    def predict(self, note_record):
        pass
    def score(self, signature, note_record):
        pass

