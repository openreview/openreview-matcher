class PaperReviewerEdgeInvitationIds:
    '''
    Keeps all the invitation ids of edges that are matcher inputs.
    '''

    def __init__ (self, score_edge_inv_ids, conflicts=None, custom_loads=None):
        self.scores_invitation_id = score_edge_inv_ids
        self.conflicts_invitation_id = conflicts
        self.custom_loads_id = custom_loads

    def get_score_names (self):
        return [self.get_score_name_from_invitation_id(inv) for inv in self.scores_invitation_id]

    @classmethod
    def get_score_name_from_invitation_id (cls, score_inv_id):
        return  score_inv_id.split('/')[-1]
