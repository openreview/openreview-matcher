from collections import defaultdict
import numpy as np
import logging
import time

from matcher.CostFunction import CostFunction
from matcher.fields import Configuration
from matcher.fields import PaperReviewerScore
from matcher.fields import Assignment
from matcher.WeightedScorer import WeightedScorer


class Encoder:

    def __init__(self, paper_reviewer_info=None, config=None, cost_func=CostFunction(), logger=logging.getLogger(__name__)):
        self.logger = logger
        self.paper_reviewer_data = paper_reviewer_info #type: PaperReviewerData
        self.config = config
        self._cost_func = cost_func

        self._cost_matrix = np.zeros((0, 0))
        self._constraint_matrix = np.zeros((0, 0))
        self._score_names = config[Configuration.SCORES_NAMES]
        self._scorer = WeightedScorer(config[Configuration.SCORES_NAMES], config[Configuration.SCORES_WEIGHTS])
        self._constraints = config.get(Configuration.CONSTRAINTS, {})

        if self.paper_reviewer_data and self.config and self.paper_reviewer_data.reviewers and self.paper_reviewer_data.paper_notes:
            self.encode()

    @property
    def cost_function (self):
        return self._cost_func

    @property
    def cost_matrix (self):
        return self._cost_matrix

    @property
    def weights (self):
        return self._weights

    def _score_to_cost (self, aggregate_score):
        return -1 * (aggregate_score / 0.01)

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
        if paper_user_scores:
            aggregate_score = self._scorer.weighted_score(paper_user_scores.scores)
            cost = self._score_to_cost(aggregate_score)
            paper_user_scores.set_aggregate_score(aggregate_score) # save aggregate score so we can generate edges from this later
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

                # assignment = self._make_assignment_record(reviewer)
                paper_user_scores = self.paper_reviewer_data.get_entry(paper_note.id, reviewer) #type : PaperUserScores

                # if entry:
                #     self._set_assignment_scores_and_conflicts(assignment, entry)
                if flow:
                    # assignments_by_forum[paper_note.id].append(assignment)
                    assignments_by_forum[paper_note.id].append(paper_user_scores)

        self.logger.debug("Done decoding.  Took {}".format(time.time() - now))
        return dict(assignments_by_forum)

    def _set_assignment_scores_and_conflicts (self, assignment, entry):
        assignment[Assignment.SCORES] = self.cost_function.weight_scores(entry, self.weights)
        assignment[Assignment.CONFLICTS] = entry.get(PaperReviewerScore.CONFLICTS)
        assignment[Assignment.FINAL_SCORE] = self.cost_function.aggregate_score(entry, self.weights)

    def _make_assignment_record (self, reviewer):
        return {
            Assignment.USERID: reviewer,
            Assignment.SCORES: {},
            Assignment.CONFLICTS: [],
            Assignment.FINAL_SCORE: None
        }