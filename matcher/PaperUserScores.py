class PaperUserScores:
    '''
    Holds scores and conflict information about a pair of paper/reviewer
    '''

    def __init__ (self):
        self._paper_id = None
        self._user = None
        self._scores_dict = {} #e.g. {'affinity': 0.2, 'recommendation': 0.5}
        self._conflicts = [] #e.g. ['umass.edu', 'google.com']
        self._aggregate_score = 0.0

    def set_paper (self, paper_id):
        self._paper_id = paper_id

    def set_user (self, user):
        self._user = user

    @property
    def user (self):
        return self._user

    @property
    def aggregate_score (self):
        return self._aggregate_score

    @property
    def scores (self):
        return self._scores_dict

    @property
    def conflicts (self):
        return self._conflicts

    def add_score (self, score_name, score):
        self._scores_dict[score_name] = score

    def set_conflicts (self, conflicts):
        self._conflicts = conflicts

    def set_aggregate_score (self, ag_score):
        self._aggregate_score = ag_score