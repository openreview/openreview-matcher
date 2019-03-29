import time

from fields import PaperReviewerScore

# This is a replacement for the old metadata note object that is passed into the encoder
# This will hold a paper_metadata map keyed on forum id where the value held there is the same as what was held in a metadata note in its content.entries field
class Metadata:

    def __init__ (self, paper_notes, reviewers, score_invitation_ids):
        self._paper_notes = paper_notes
        self._reviewers = reviewers
        self._score_invitation_ids = score_invitation_ids
        self._entries_by_forum_map = {}

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
    def reviewers_by_forum_map (self):
        return self._entries_by_forum_map


    def get_entry (self, paper_id, reviewer):
        return self._entries_by_forum_map[paper_id][reviewer]

    def len (self):
        return len(self.paper_notes)

    def translate_score_inv_to_score_name (self, score_inv_id):
        score_name = score_inv_id.split('/')[-1]  # like Bid or Affinity
        return score_name.lower() # case has to match the list of score_names in the config note which are lower case

    # create a dict keyed by forum_id.  each forum id maps to a dict keyed by reviewer-id which maps to an entry dict like:
    # {"forum-1": {"reviewer-1": {affinity: 0.4, bid: 3}, "reviewer-2": {..}, ...}, "forum-2": {...} }
    def load_data (self, or_client):
        print("Loading meta data from edges")
        now = time.time()
        for paper in self._paper_notes:
            self._entries_by_forum_map[paper.id] = {}
            for reviewer in self._reviewers:
                entry = {}
                for score_inv_id in self._score_invitation_ids:
                    score_name = self.translate_score_inv_to_score_name(score_inv_id)
                    edge = or_client.get_edges(invitation=score_inv_id, head=paper.id, tail=reviewer)
                    if edge:
                        edge = edge[0] # There can only be one edge with this score, head, tail
                        entry[score_name] = edge.weight
                self._entries_by_forum_map[paper.id][reviewer] = entry
        print("Done loading meta data from edges.  Took", time.time() - now)






