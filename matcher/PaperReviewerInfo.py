import openreview.tools
import time
import logging
from collections import defaultdict
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds

# This is a replacement for the old metadata note object that is passed into the encoder
# This will hold a paper_metadata map keyed on forum id where the value held there is the same as what was held in a metadata note in its content.entries field
from fields import PaperReviewerScore
# Module contains two classes PaperReviewerInfo and PaperReviewerEdgeInvitationIds

class PaperReviewerInfo:

    def __init__ (self, client, config_title, paper_notes, reviewers, edge_invitations, logger=logging.getLogger(__name__), map=None):
        self.logger = logger
        self.config_title = config_title
        self._paper_notes = paper_notes
        self._reviewers = reviewers
        self.edge_invitations = edge_invitations # type: PaperReviewerEdgeInvitationIds
        self._scores_invitation_ids = edge_invitations.scores_invitation_id
        self._score_names = [self.translate_score_inv_to_score_name(inv) for inv in edge_invitations.scores_invitation_id]
        if map:
            self._entries_by_forum_map = map
        else:
            self.load_scores(client)
            self.load_conflicts(client)
            self.load_constraints(client)

    @property
    def paper_notes (self):
        return self._paper_notes

    @property
    def reviewers (self):
        return self._reviewers

    @property
    def score_invitation_ids (self):
        return self._scores_invitation_ids

    @property
    def entries_by_forum_map (self):
        return self._entries_by_forum_map

    # Public iterator which provides forum_id, reviewer-dict of items in this class's internals
    def items (self):
        return self._entries_by_forum_map.items()

    def get_entry (self, paper_id, reviewer):
        val = self._entries_by_forum_map[paper_id].get(reviewer, {})
        return val

    def len (self):
        return len(self.paper_notes)

    # translate the invitation id to a score name by plucking off the last piece of the invitation id
    def translate_score_inv_to_score_name (self, score_inv_id):
        score_name = score_inv_id.split('/')[-1]  # like bid, tpms, subjectArea
        return score_name

    # Test to see if any score data was given for the reviewer in a given forum.
    def has_score_data (self, forum_id, reviewer):
        entry = self._entries_by_forum_map[forum_id].get(reviewer,{})
        for score_name in self._score_names:
            if entry.get(score_name):
                return True
        return False

    def load_scores (self, or_client):
        now = time.time()
        self.logger.debug("Loading metadata from edges")
        self._entries_by_forum_map = defaultdict(defaultdict)
        num_entries = 0
        for score_index, inv_id in enumerate(self.score_invitation_ids):
            score_name = self._score_names[score_index]
            edges = openreview.tools.iterget_edges(or_client, invitation=inv_id, limit=50000)
            for e in edges:
                if self._entries_by_forum_map[e.head].get(e.tail):
                    self._entries_by_forum_map[e.head][e.tail][score_name] = e.weight
                else:
                    num_entries += 1
                    self._entries_by_forum_map[e.head][e.tail] = {score_name:  e.weight}
        self.logger.debug("Done loading metadata from edges.  Number of score entries:" + str(num_entries) + "Took:" + str(time.time() - now))

    def load_constraints (self, or_client):
        constraints_inv_id = self.edge_invitations.constraints_invitation_id
        # check label == config-note.title because constraints are set for each config
        edges = openreview.tools.iterget_edges(or_client, invitation=constraints_inv_id, label=self.config_title, limit=50000)
        for e in edges:
            if self._entries_by_forum_map[e.head].get(e.tail):
                self._entries_by_forum_map[e.head][e.tail]['constraint'] = e.weight
            else:
                self._entries_by_forum_map[e.head][e.tail] = {'constraint': e.weight}

    def load_conflicts (self, or_client):
        conflicts_inv_id = self.edge_invitations.conflicts_invitation_id
        edges = openreview.tools.iterget_edges(or_client, invitation=conflicts_inv_id, limit=50000)
        # Assumption: Conflicts are defined at the conference level.   For now, I'm assuming a pre-processing step which
        # produces conflicts edges that contain lists of domains in the label of the conflict with the weight empty.
        # TODO If conflict detection between reviewer and paper is not a pre-processing step,  it would be calculated here
        for e in edges:
            if self._entries_by_forum_map[e.head].get(e.tail):
                self._entries_by_forum_map[e.head][e.tail]['conflicts'] = e.label
            else:
                self._entries_by_forum_map[e.head][e.tail] = {'conflicts': e.label}

    # Temporary implementation using metadata notes so that I can load this object correctly with
    # conflict info (which will eventually be given as edges)
    def add_conflicts (self, metadata_notes):
        for md_note in metadata_notes:
            forum_id = md_note.forum
            for entry in md_note.content['entries']:
                userid = entry[PaperReviewerScore.USERID]
                conflicts = entry.get(PaperReviewerScore.CONFLICTS)
                if conflicts:
                    if self._entries_by_forum_map[forum_id].get(userid):
                        self._entries_by_forum_map[forum_id][userid]['conflicts'] = conflicts
                    else:
                        self._entries_by_forum_map[forum_id][userid] = {'conflicts': conflicts}


    # Temporary implementation using config dictionary so that I can load this object correctly with
    # constraints info (which will eventually be given as edges)
    def add_constraints (self, constraints_dict):
        for forum_id, reviewers in constraints_dict.items():
            for reviewer, val in reviewers.items():
                if self._entries_by_forum_map[forum_id].get(reviewer):
                    self._entries_by_forum_map[forum_id][reviewer]['constraint'] = val
                else:
                    self._entries_by_forum_map[forum_id][reviewer] = {'constraint': val}


    def get_coords (self, rev, forum_id):
        for i, paper in enumerate(self.paper_notes):
            if paper.id == forum_id:
                break

        pix = i
        rix = self.reviewers.index(rev)
        return rix, pix




