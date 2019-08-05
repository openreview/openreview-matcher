import openreview.tools
import time
import logging
from matcher.PaperUserScores import PaperUserScores
from matcher.EdgeFetcher import EdgeFetcher
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
from matcher.fields import Configuration
from exc.exceptions import TranslateScoreError, ScoreEdgeMissingWeightError


class PaperReviewerData:
    '''
    All scoring information about a conference's papers and reviewers (a replacement for metadata notes).
    Each pair <Paper,Reviewer> has scoring and conflict info stored in a PaperUserScores object.  This
    class creates these objects (from the score & conflict edges) and puts them in a map keyed by forum_id and reviewer
    that then provides fast access to this info.
    '''

    def __init__ (self, paper_notes, reviewers, edge_invitations, score_specification, edge_fetcher, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.edge_fetcher = edge_fetcher # type: EdgeFetcher
        self.edge_invitations = edge_invitations # type: PaperReviewerEdgeInvitationIds
        # a map like: {'forum_id-1' : {'reviewer-1' : PaperUserScores, ...}, ... } produces empty PaperUserScores objects by default
        self._score_map = {}
        self._paper_notes = paper_notes
        self._reviewers = reviewers
        # self._aggregate_score_cutoff
        self._score_specification = score_specification # dict mapping score-invitation_ids to a dict of weight,default,translate_fn
        self._load_score_map()

    @property
    def paper_notes (self):
        return self._paper_notes

    @property
    def reviewers (self):
        return self._reviewers

    # iterator through the map of PaperUserScores objects
    def items (self):
        return self._score_map.items()

    def get_paper_data (self, paper_id):
        return self._score_map[paper_id]

    # Will return an empty PaperUserScores object if none is mapped
    def get_entry (self, paper_id, reviewer):
        return self._score_map[paper_id][reviewer]


    # Overwrite scores in the PaperUserScores stored in the scores_map with scores coming from edges.
    def _load_scores_from_edges (self):
        now = time.time()
        scores_invitation_ids = self.edge_invitations.scores_invitation_id
        score_names = self.edge_invitations.get_score_names()
        self.logger.debug("Loading score entries from edges")
        num_entries = 0
        for score_index, inv_id in enumerate(scores_invitation_ids):
            score_name = score_names[score_index]
            for score_edge in self.edge_fetcher.get_all_edges(inv_id):
                forum_id = score_edge.head
                reviewer = score_edge.tail

                # skip edges whose nodes are not in the score map
                # (e.g. deleted papers or removed reviewers)
                if self._score_map.get(forum_id) and self._score_map[forum_id].get(reviewer):
                    paper_user_scores = self._score_map[forum_id][reviewer]
                    score_spec = self._score_specification[inv_id]
                    score = self._translate_edge_to_score(score_spec, score_edge)
                    weighted_score = score * score_spec[Configuration.SCORE_WEIGHT]
                    paper_user_scores.set_score(score_name, weighted_score)
                    num_entries += 1

        self.logger.debug("Done loading score entries from edges.  Number of score entries:" + str(num_entries) + "Took:" + str(time.time() - now))




    # The translate function for each score name does the job of converting a symbolic score to a number.
    def _translate_edge_to_score (self, score_spec, edge):
        translate_map = score_spec.get(Configuration.SCORE_TRANSLATE_MAP)
        # if using a map, the assumption is that the edge label is holding a symbol that needs to be translated via the map
        if translate_map:
            try:
                numeric_score = translate_map[edge.label]
                float(numeric_score)
                return numeric_score
            except:
                raise TranslateScoreError("Cannot translate score: {} of edge {}->{}.  Check the translate_map within scores_specification of the configuration note".format(edge.label, edge.head, edge.tail) )
        elif edge.label and not edge.weight:
            raise TranslateScoreError("No translate_map provided for this edge {}->{} ".format(edge.head, edge.tail))
        else:
            numeric_score = edge.weight
            try:
                float(numeric_score) # convert to float here so it will throw ValueError if not a number
                return numeric_score
            except:
                raise ScoreEdgeMissingWeightError("Score edge {}->{} is missing a label and its weight {} is non-numeric".format(edge.head, edge.tail, edge.weight))

    # fully populates the score map with PaperUserScores records that have scores based on defaults.
    def _load_score_map_with_default_scores (self):
        self._score_map = {}
        for paper_note in self.paper_notes:
            self._score_map[paper_note.id] = {}
            for reviewer in self.reviewers:
                self._score_map[paper_note.id][reviewer] = self._create_paper_user_scores_from_default(paper_note.id, reviewer)


    # Create the record initialized with the weighted default value for each score
    def _create_paper_user_scores_from_default (self, paper_id, reviewer):
        score_rec = PaperUserScores(paper_id, reviewer)
        for score_edge_inv, spec in self._score_specification.items():
            score_name = PaperReviewerEdgeInvitationIds.get_score_name_from_invitation_id(score_edge_inv)
            weighted_score = spec[Configuration.SCORE_DEFAULT] * spec[Configuration.SCORE_WEIGHT]
            score_rec.set_score(score_name, weighted_score)
        return score_rec


    def _load_conflicts (self):
        conflicts_inv_id = self.edge_invitations.conflicts_invitation_id
        if conflicts_inv_id:
            for score_edge in self.edge_fetcher.get_all_edges(conflicts_inv_id):
                forum_id = score_edge.head
                # skip edges that refer to missing papers or users
                if not self._score_map.get(forum_id) or not self._score_map[forum_id].get(score_edge.tail):
                        continue
                paper_user_scores = self._score_map[forum_id][score_edge.tail]
                paper_user_scores.set_conflicts(score_edge.label) # will be a list of domains stored in the label

    def _load_score_map (self):
        self._load_score_map_with_default_scores() # fully populate the map with default info
        self._load_scores_from_edges() # overwrite scores when an edge is provided
        self._load_conflicts()



