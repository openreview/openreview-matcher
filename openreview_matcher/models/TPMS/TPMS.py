from openreview_matcher.models import base_model
from openreview_matcher import utils
import pickle


class Model(base_model.Model):

    def __init__(self, combinining_mechanism, scoring_mechanism, keyphrase_extractor, params=None):
        self.tpms_file_location = "./openreview_matcher/models/tpms/iccv15_tpms_scores.pkl"
        self.tpms_scores = None

    def fit(self, train_data, archive_data):
        self.tpms_scores = self.__open_tpms_scores()

    def predict(self, note_record):
        """ Returns the reviewer ranks for query paper """

        forum_id = note_record["forum"]
        sorted_reviewer_scores = sorted([(scores["score"], scores["signature"].replace(" ", "_")) for scores in self.tpms_scores[forum_id]], reverse=True)
        ranked_reviewer_list = ["{0};{1}".format(reviewer_scores[1].encode('utf-8'),reviewer_scores[0]) for
                                reviewer_scores in sorted_reviewer_scores]
        return ranked_reviewer_list

    def score(self, signature, note_record):
        """ Returns a score between a signature (reviewer id) and a note_record """
        pass

    def __open_tpms_scores(self):
        """ Load in the TPMS Scores """
        with open(self.tpms_file_location, "r") as f:
            return pickle.load(f)

