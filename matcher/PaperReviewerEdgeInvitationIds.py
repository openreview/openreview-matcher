class PaperReviewerEdgeInvitationIds:
    '''
    Keeps all the invitation ids of edges that are matcher inputs.
    '''

    def __init__ (self, score_edge_inv_ids, conflicts=None, custom_loads=None):
        self.scores_invitation_id = score_edge_inv_ids
        self.conflicts_invitation_id = conflicts
        self.custom_loads_id = custom_loads

    def get_score_names (self):
        return [self.translate_score_inv_to_score_name(inv) for inv in self.scores_invitation_id]

    # translate the invitation id to a score name by plucking off the last piece of the invitation id
    @staticmethod
    def translate_score_inv_to_score_name (score_inv_id):
        score_name = score_inv_id.split('/')[-1]  # like bid, tpms, subjectArea
        return score_name
