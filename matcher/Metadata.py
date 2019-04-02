import time

from fields import PaperReviewerScore
import openreview.tools
from collections import defaultdict

# This is a replacement for the old metadata note object that is passed into the encoder
# This will hold a paper_metadata map keyed on forum id where the value held there is the same as what was held in a metadata note in its content.entries field
class Metadata:

    def __init__ (self, client, paper_notes, reviewers, score_invitation_ids):
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
        return self._entries_by_forum_map[paper_id][reviewer]

    def len (self):
        return len(self.paper_notes)

    # translate the invitation id to a score name
    def translate_score_inv_to_score_name (self, score_inv_id):
        score_name = score_inv_id.split('/')[-1]  # like Bid or Affinity
        return score_name.lower() # case has to match the list of score_names in the config note which are lower case


    def load_data (self, or_client):
        self._entries_by_forum_map = defaultdict(defaultdict)
        for count, inv_id in enumerate(self.score_invitation_ids):
            score_name = self.translate_score_inv_to_score_name(inv_id)
            edges = openreview.tools.iterget_edges(or_client,invitation=inv_id)
            for e in edges:
                if self._entries_by_forum_map[e.head].get(e.tail):
                    self._entries_by_forum_map[e.head][e.tail][score_name] = e.weight
                else:
                    self._entries_by_forum_map[e.head][e.tail] = {score_name:  e.weight}











