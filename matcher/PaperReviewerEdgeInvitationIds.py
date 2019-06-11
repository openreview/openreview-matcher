import util.names

class PaperReviewerEdgeInvitationIds:
    '''
    Keeps all the invitation ids of edges that are matcher inputs.
    '''

    def __init__ (self, score_edge_inv_ids, conflicts=None, custom_loads=None):
        self.scores_invitation_id = score_edge_inv_ids
        self.conflicts_invitation_id = conflicts
        self.custom_loads_id = custom_loads

    def get_score_names (self):
        return [util.names.translate_score_inv_to_score_name(inv) for inv in self.scores_invitation_id]


