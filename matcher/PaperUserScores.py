import util.names
from matcher.fields import Configuration
class PaperUserScores:
    '''
    Holds scores and conflict information about a pair of paper/reviewer
    '''

    def __init__ (self, forum_id=None, reviewer=None):
        self._paper_id = forum_id
        self._user = reviewer
        self._scores_dict = {} #e.g. {'affinity': 0.2, 'recommendation': 0.5}
        self._conflicts = [] #e.g. ['umass.edu', 'google.com']


    @property
    def user (self):
        return self._user

    @property
    def scores (self):
        return self._scores_dict

    @property
    def conflicts (self):
        return self._conflicts

    def add_score (self, score_name, score):
        print('add score', score_name, score)
        self._scores_dict[score_name] = score

    def set_conflicts (self, conflicts):
        self._conflicts = conflicts

    def get_aggregate_score(self):
        return sum(self._scores_dict.values())

    def calculate_aggregrate_score (self, score_specs):
        '''
        Computes the weighted sum of the individual scores.  If an individual score was present on an edge, then it will have been run through a translate function
        (PaperReviewerData._load_scores does this).  If no edge exists for a score, this will use its default value and weight in computing the sum.
        :param score_spec:
        :return:
        '''
        ag_score = 0
        for score_edge_inv_id, score_spec in score_specs.items():
            score_name = util.names.translate_score_inv_to_score_name(score_edge_inv_id)
            score = self.scores.get(score_name) # gets score provided by an edge or None if edge did not provide it.
            if not score:
                # must be expressed numerically because we cannot call the translate_fn here to convert (since score edge is the input to the translate function)
                score = score_spec[Configuration.SCORE_DEFAULT]
            weighted_score = score_spec[Configuration.SCORE_WEIGHT] * score
            ag_score += weighted_score
        return ag_score


