import openreview.tools
import time
import logging
from collections import defaultdict
from matcher.PaperUserScores import PaperUserScores
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds


class PaperReviewerData:
    '''
    All scoring information about a conference's papers and reviewers (a replacement for metadata notes).
    Each pair <Paper,Reviewer> has scoring and conflict info stored in a PaperUserScores object.  This
    class creates these objects (from the score & conflict edges) and puts them in a map keyed by forum_id and reviewer
    that then provides fast access to this info.
    '''

    def __init__ (self, client, paper_notes, reviewers, edge_invitations, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.edge_invitations = edge_invitations # type: PaperReviewerEdgeInvitationIds
        # a map like: {'forum_id-1' : {'reviewer-1' : PaperUserScores, ...}, ... } produces empty PaperUserScores objects by default
        self._score_map = defaultdict(lambda: defaultdict(PaperUserScores))
        self._paper_notes = paper_notes
        self._reviewers = reviewers
        self._load_scores(client)
        self._load_conflicts(client)

    @property
    def paper_notes (self):
        return self._paper_notes

    @property
    def reviewers (self):
        return self._reviewers

    # iterator through the map of PaperUserScores objects
    def items (self):
        return self._score_map.items()

    # since _score_map is a defaultdict, it will return an empty one if none stored
    def get_entry (self, paper_id, reviewer):
        return self._score_map[paper_id][reviewer]

    # build map from the score edges.
    def _load_scores (self, or_client):
        now = time.time()
        scores_invitation_ids = self.edge_invitations.scores_invitation_id
        score_names = self.edge_invitations.get_score_names()
        self.logger.debug("Loading score entries from edges")
        num_entries = 0
        for score_index, inv_id in enumerate(scores_invitation_ids):
            score_name = score_names[score_index]
            edges = openreview.tools.iterget_edges(or_client, invitation=inv_id, limit=50000)
            for e in edges:
                paper_user_scores = self._score_map[e.head][e.tail] #type: PaperUserScores
                paper_user_scores.set_paper(e.head)
                paper_user_scores.set_user(e.tail)
                paper_user_scores.add_score(score_name, e.weight)
                num_entries += 1
        self.logger.debug("Done loading score entries from edges.  Number of score entries:" + str(num_entries) + "Took:" + str(time.time() - now))


    def _load_conflicts (self, or_client):
        conflicts_inv_id = self.edge_invitations.conflicts_invitation_id
        edges = openreview.tools.iterget_edges(or_client, invitation=conflicts_inv_id, limit=50000)
        # Assumption: Conflicts are defined at the conference level.   For now, I'm assuming a pre-processing step which
        # produces conflicts edges that contain lists of domains in the label of the conflict with the weight empty.
        # TODO If conflict detection between reviewer and paper is not a pre-processing step and becomes part of the matching process itself,
        # it could be calculated here
        for e in edges:
            paper_user_scores = self._score_map[e.head][e.tail] #type: PaperUserScores
            paper_user_scores.set_paper(e.head)
            paper_user_scores.set_user(e.tail)
            paper_user_scores.set_conflicts(e.label)


