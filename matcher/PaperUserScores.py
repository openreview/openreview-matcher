class PaperUserScores:
    '''
    Holds scores and conflict information about a pair of paper/reviewer
    '''

    def __init__ (self, forum_id=None, reviewer=None):
        self._paper_id = forum_id
        self._user = reviewer
        self._scores_dict = {} #e.g. {'affinity': 0.2, 'recommendation': 0.5}  N.B. Scores are weighted.
        self._conflicts = [] #e.g. ['umass.edu', 'google.com']
        self._aggregate_score = 0

    @property
    def user (self):
        return self._user

    @property
    def scores (self):
        return self._scores_dict

    @property
    def aggregate_score (self):
        return sum(self._scores_dict.values())


    @property
    def conflicts (self):
        return self._conflicts

    # Stores a score (which should be weighted)
    def set_score (self, score_name, score):
        self._scores_dict[score_name] = score

    def set_conflicts (self, conflicts):
        self._conflicts = conflicts


