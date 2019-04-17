import openreview.tools
from exc.exceptions import NotFoundError
import time
import logging
from collections import defaultdict

# This is a replacement for the old metadata note object that is passed into the encoder
# This will hold a paper_metadata map keyed on forum id where the value held there is the same as what was held in a metadata note in its content.entries field
from fields import PaperReviewerScore

class MetadataEdgeInvitationIds:

    def __init__ (self, scores, conflicts=None, constraints=None, custom_loads=None):
        self.scores_invitation_id = scores
        self.conflicts_invitation_id = conflicts
        self.constraints_invitation_id = constraints
        self.custom_loads_id = custom_loads


class Metadata:

    def __init__ (self, client, config_title, paper_notes, reviewers, edge_invitations, logger=logging.getLogger(__name__), map=None):
        self.logger = logger
        self.config_title = config_title
        self._paper_notes = paper_notes
        self._reviewers = reviewers
        self.edge_invitations = edge_invitations # type: MetadataEdgeInvitationIds
        self._scores_invitation_ids = edge_invitations.scores_invitation_id
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


    def get_entry (self, paper_id, reviewer):
        val = self._entries_by_forum_map[paper_id].get(reviewer, {})
        return val

    def len (self):
        return len(self.paper_notes)

    # translate the invitation id to a score name by plucking off the last piece of the invitation id
    def translate_score_inv_to_score_name (self, score_inv_id):
        score_name = score_inv_id.split('/')[-1]  # like bid, tpms, subjectArea
        return score_name


    def load_scores (self, or_client):
        now = time.time()
        self.logger.debug("Loading metadata from edges")
        self._entries_by_forum_map = defaultdict(defaultdict)
        for inv_id in self.score_invitation_ids:
            score_name = self.translate_score_inv_to_score_name(inv_id)
            edges = openreview.tools.iterget_edges(or_client, invitation=inv_id, limit=50000)
            for e in edges:
                if self._entries_by_forum_map[e.head].get(e.tail):
                    self._entries_by_forum_map[e.head][e.tail][score_name] = e.weight
                else:
                    self._entries_by_forum_map[e.head][e.tail] = {score_name:  e.weight}
        self.logger.debug("Done loading metadata from edges.  Took:" + str(time.time() - now))

    def load_constraints (self, or_client):
        constraints_inv_id = self.edge_invitations.constraints_invitation_id
        # The constraints query has to ask for its label == config-note.title because constraints are set for each config
        # The problem with this is that weight is not a number.  It's a '-inf' or '+inf'.   This won't work if edge validation rejects the string.
        edges = openreview.tools.iterget_edges(or_client, invitation=constraints_inv_id, label=self.config_title, limit=50000)
        for e in edges:
            if self._entries_by_forum_map[e.head].get(e.tail):
                self._entries_by_forum_map[e.head][e.tail]['constraint'] = e.weight
            else:
                self._entries_by_forum_map[e.head][e.tail] = {'constraint': e.weight}

    def load_conflicts (self, or_client):
        conflicts_inv_id = self.edge_invitations.conflicts_invitation_id
        edges = openreview.tools.iterget_edges(or_client, invitation=conflicts_inv_id, limit=50000)
        # TODO Conflicts are defined at the conference level.   For now, I'm assuming a pre-processing step which
        # produces conflicts edges that contain lists of domains in the label of the conflict with the weight empty.
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





