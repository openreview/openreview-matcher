from util.PythonFunctionRunner import ORFunctionRunner
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

    def calculate_aggregrate_score (self, score_specs):
        '''
        Computes the weighted sum of the individual scores.  If an individual score was present on an edge, then it will have been run through a translate function
        (PaperReviewerData._load_scores does this).  If no edge exists for a score, this will use its default value and weight in computing the sum.
        :param score_spec:
        :return:
        '''
        ag_score = 0
        for score_name, score_spec in score_specs.items():
            score = self.scores.get(score_name) # gets score provided by an edge or None if edge did not provide it.
            if not score:
                # must be expressed numerically because we cannot call the translate_fn here to convert (since score edge is the input to the translate function)
                score = score_spec['default']
            weighted_score = score_spec['weight'] * score
            ag_score += weighted_score
        return ag_score


    # e.g. score_dict {affinity: 0.3, recommendation: 0.4} (possibly some scores missing)
    # score_spec is dict that defines each score's default and possibly a function to convert the score to a number
    def set_weighted_score (self, score_spec):
        '''
        :return: The weighted sum of all the scores (called the "aggregate score")
        '''
        total_score = 0
        for score_name, spec_dict in score_spec.items():
            weight = spec_dict['weight']
            default = spec_dict['default']
            translate_fn = spec_dict.get('translate_fn')
            score = self.scores.get(score_name, default)
            if translate_fn:
                score = self._translate_score(score, translate_fn)
            total_score += weight * score
        self.set_aggregate_score(total_score)
        return total_score

    # If a score_val is not a number it will need to be translated to one by a user-defined lambda expression like:
    # 'lambda x : return 0.9 if x == 'good' else 0.3' .
    def _translate_score (self, score_val, translate_fn):
        #TODO passing an or-Client is messy because this object is only used by the Encoder which intentionally has no access
        #to the db.
        runner = ORFunctionRunner(translate_fn, or_client=None, forum_id=self._paper_id, reviewer=self._user)
        runner.add_additional_symbols_dict(self._paper_id, self._user)
        result = runner.run_function(score_val)
        return result