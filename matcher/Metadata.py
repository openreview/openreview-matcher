import time

from fields import PaperReviewerScore
import openreview.tools
from collections import defaultdict

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
    def entries_by_forum_map (self):
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
    # This is too slow for a large data set because each paper-reviewer + score is an individual edge query that takes too long.

    def load_data1 (self, or_client):
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

    def load_data (self, or_client):
        print("Loading meta data from edges")
        now = time.time()
        edge_maps = []
        #Create EdgeMgr dictionaries for each score invitation
        for inv in self.score_invitation_ids:
            m =  EdgeMap(or_client)
            m.load_edges(inv)
            edge_maps.append(m)

        # for each paper-reviewer pair, get its edges for scores and build an entry holding scores from the weights of the edges
        for paper in self._paper_notes:
            self._entries_by_forum_map[paper.id] = {}
            for reviewer in self._reviewers:
                entry = {}
                for i, score_inv_id in enumerate(self._score_invitation_ids):
                    score_name = self.translate_score_inv_to_score_name(score_inv_id)
                    edge = edge_maps[i].get_edge(paper.id,reviewer)
                    # edge = or_client.get_edges(invitation=score_inv_id, head=paper.id, tail=reviewer)[0]
                    if edge:
                        entry[score_name] = edge.weight
                self._entries_by_forum_map[paper.id][reviewer] = entry
        print("Done loading meta data from edges.  Took", time.time() - now)


class EdgeMap:

    def __init__(self, or_client):
        self.or_client = or_client
        self.edge_map = defaultdict(dict)

    # edge_map will map head ids to a dict of tail ids which then map to the edge.   This will support
    # lookup by head + tail
    def load_edges (self, invitation):
        edges = list(openreview.tools.iterget_edges(self.or_client,invitation=invitation))
        for e in edges:
            self.edge_map[e.head][e.tail] = e


    def get_edge (self, head, tail):
        return self.edge_map[head][tail]










