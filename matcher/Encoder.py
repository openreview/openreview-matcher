from collections import defaultdict
import numpy as np
import logging
import time

from matcher.fields import Configuration
import matcher.cost_function


class Encoder:

    def __init__(self, paper_reviewer_data=None, cost_fn=matcher.cost_function.aggregate_score_to_cost, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.paper_reviewer_data = paper_reviewer_data #type: PaperReviewerData
        self._cost_matrix = np.zeros((0, 0))
        self._constraint_matrix = np.zeros((0, 0))
        self._cost_fn = cost_fn
        if self.paper_reviewer_data and self.paper_reviewer_data.reviewers and self.paper_reviewer_data.paper_notes:
            self.encode()

    @property
    def cost_matrix (self):
        return self._cost_matrix

    @property
    def weights (self):
        return self._weights

    def encode (self):
        self.logger.debug("Encoding")
        now = time.time()
        self._cost_matrix = np.zeros((len(self.paper_reviewer_data.reviewers), len(self.paper_reviewer_data.paper_notes)))
        self._constraint_matrix = np.zeros(np.shape(self._cost_matrix))
        for reviewer_index, reviewer in enumerate(self.paper_reviewer_data.reviewers):
            for paper_index, paper_note in enumerate(self.paper_reviewer_data.paper_notes):
                paper_user_scores = self.paper_reviewer_data.get_entry(paper_note.id, reviewer)
                self._update_cost_matrix(paper_user_scores, reviewer_index, paper_index)
                self._update_constraint_matrix(paper_user_scores, reviewer_index, paper_index)
        self.logger.debug("Done encoding.  Took {}".format(time.time() - now))

    def _update_cost_matrix (self, paper_user_scores, reviewer_index, paper_index):
        coordinates = reviewer_index, paper_index
        cost = self._cost_fn(paper_user_scores.aggregate_score)
        self._cost_matrix[coordinates] = cost

    # Conflicts between paper/reviewer sets the constraint matrix cell to -1 ; 0 otherwise
    def _update_constraint_matrix (self, paper_user_scores, reviewer_index, paper_index):
        coordinates = reviewer_index, paper_index
        self._constraint_matrix[coordinates] = -1 if paper_user_scores.conflicts else 0


    def decode (self, flow_matrix):
        now = time.time()
        self.logger.debug("Decoding")
        assignments_by_forum = defaultdict(list)

        for reviewer_index, reviewer_flows in enumerate(flow_matrix):
            reviewer = self.paper_reviewer_data.reviewers[reviewer_index]
            for paper_index, flow in enumerate(reviewer_flows):
                paper_note = self.paper_reviewer_data.paper_notes[paper_index]
                paper_user_scores = self.paper_reviewer_data.get_entry(paper_note.id, reviewer) #type : PaperUserScores
                if flow:
                    assignments_by_forum[paper_note.id].append(paper_user_scores)

        self.logger.debug("Done decoding.  Took {}".format(time.time() - now))
        return dict(assignments_by_forum)
