class WeightedScorer:
    '''
    Class that contains definition about weighted scoring of a reviewer to a paper
    '''

    DEFAULT_VALUE = 0

    def __init__ (self, score_names, score_weights):
        self.weight_dict = self._get_weight_dict(score_names, score_weights)

    def _get_weight_dict (self, names, weights):
        return dict(zip(names, [ float(w) for w in weights]))

    # e.g. score_dict {affinity: 0.3, recommendation: 0.4}
    def weighted_score (self, score_dict):
        s = 0
        for score_name, weight in self.weight_dict.items():
            s += weight * self._get_score(score_dict, score_name)
        return s


    # get the score from score_dict if its there; else the default
    # TODO For now we assume the score is just a number and if missing we use the class DEFAULT_VALUE.  In the future
    # each score may have its own default and a score may not be a number.  It could be a symbol or some other thing that would need to be sent
    # through some function (perhaps defined by the user) to be converted to a number (e.g. bids are set to "very high", "high" ... and need to be converted to numbers based
    # on a user-defined conversion function.  Same with subjectArea which is a list of topics in the paper and in the reviewer
    def _get_score (self, score_dict, score_name):
        return score_dict.get(score_name, WeightedScorer.DEFAULT_VALUE)