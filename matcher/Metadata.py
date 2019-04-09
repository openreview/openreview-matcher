import openreview.tools
from exc.exceptions import NotFoundError
import time
import logging
from collections import defaultdict

# This is a replacement for the old metadata note object that is passed into the encoder
# This will hold a paper_metadata map keyed on forum id where the value held there is the same as what was held in a metadata note in its content.entries field
class Metadata:

    def __init__ (self, client, paper_notes, reviewers, score_invitation_ids, logger=logging.getLogger(__name__)):
        self.logger = logger
        self._paper_notes = paper_notes
        self._reviewers = reviewers
        self._score_invitation_ids = score_invitation_ids
        self._entries_by_forum_map = {}
        self.load_data(client)

    @property
    def paper_notes (self):
        return self._paper_notes

    @property
    def reviewers (self):
        return self._reviewers

    @property
    def score_invitation_ids (self):
        return self._score_invitation_ids

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


    def load_data (self, or_client):
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











