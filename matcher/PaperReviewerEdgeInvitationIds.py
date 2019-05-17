class PaperReviewerEdgeInvitationIds:

    def __init__ (self, scores, conflicts=None, constraints=None, custom_loads=None):
        self.scores_invitation_id = scores
        self.conflicts_invitation_id = conflicts
        self.constraints_invitation_id = constraints
        self.custom_loads_id = custom_loads

    def get_score_names (self):
        return [self._translate_score_inv_to_score_name(inv) for inv in self.scores_invitation_id]

    # translate the invitation id to a score name by plucking off the last piece of the invitation id
    def _translate_score_inv_to_score_name (self, score_inv_id):
        score_name = score_inv_id.split('/')[-1]  # like bid, tpms, subjectArea
        return score_name
