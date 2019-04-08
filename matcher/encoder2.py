from collections import defaultdict
import numpy as np

from . import utils
from matcher.fields import Configuration
from matcher.fields import PaperReviewerScore
from matcher.fields import Assignment


class Encoder2:


    def __init__(self, metadata=None, config=None, reviewers=None, cost_func=utils.cost):

        self.metadata = metadata
        self.config = config
        self.cost_func = cost_func

        self.cost_matrix = np.zeros((0, 0))
        self.constraint_matrix = np.zeros((0, 0))
        self.score_names = config[Configuration.SCORES_NAMES]
        self.weights = self._get_weight_dict(config[Configuration.SCORES_NAMES], config[Configuration.SCORES_WEIGHTS] )
        self.constraints = config.get(Configuration.CONSTRAINTS,{})

        if self.metadata and self.config and self.metadata.reviewers and self.metadata.paper_notes:
            self.encode()

    def _get_weight_dict (self, names, weights):
        return dict(zip(names, [ float(w) for w in weights]))


    # extract the scores from the entry record to form a vector that is ordered the same as the score_names (and weights)
    def order_scores (self, entry):
        scores = []
        for score_name in self.score_names:
            scores.append(entry[score_name])
        return scores


    def update_cost_matrix (self, entry, reviewer_index, paper_index):
        coordinates = reviewer_index, paper_index
        if entry:
            self.cost_matrix[coordinates] = self.cost_func(entry, self.weights)
            if entry.get(PaperReviewerScore.CONFLICTS):
                self.constraint_matrix[coordinates] = -1
            else:
                self.constraint_matrix[coordinates] = 0

    def update_constraint_matrix (self, entry, reviewer_index, paper_index):
        pass
        '''
        # overwrite constraints with user-added constraints found in config
        user_constraint = self.constraints.get(forum, {}).get(id)
        if user_constraint:
            if Configuration.VETO in user_constraint:
                self.constraint_matrix[coordinates] = -1
            if Configuration.LOCK in user_constraint:
                self.constraint_matrix[coordinates] = 1
        '''


    def encode (self):
        self.cost_matrix = np.zeros((len(self.metadata.reviewers), len(self.metadata.paper_notes)))
        self.constraint_matrix = np.zeros(np.shape(self.cost_matrix))
        for paper_index, paper_note in enumerate(self.metadata.paper_notes):
            for reviewer_index, reviewer in enumerate(self.metadata.reviewers):
                entry = self.metadata.get_entry(paper_note.id, reviewer)
                self.update_cost_matrix(entry,reviewer_index, paper_index)
                self.update_constraint_matrix(entry, reviewer_index, paper_index)


    def decode (self, flow_matrix):
        assignments_by_forum = defaultdict(list)
        alternates_by_forum = defaultdict(list)
        for reviewer_index, reviewer_flows in enumerate(flow_matrix):
            reviewer = self.metadata.reviewers[reviewer_index]

            for paper_index, flow in enumerate(reviewer_flows):
                paper_note = self.metadata.paper_notes[paper_index]

                assignment = {
                    Assignment.USERID: reviewer,
                    Assignment.SCORES: {},
                    Assignment.CONFLICTS: [],
                    Assignment.FINAL_SCORE: None
                }
                entry = self.metadata.get_entry(paper_note.id, reviewer)

                if entry:
                    assignment[Assignment.SCORES] = utils.weight_scores(entry, self.weights)
                    assignment[Assignment.CONFLICTS] = entry.get(PaperReviewerScore.CONFLICTS)
                    assignment[Assignment.FINAL_SCORE] = utils.safe_sum(
                        utils.weight_scores(entry, self.weights).values())

                if flow:
                    assignments_by_forum[paper_note.id].append(assignment)
                elif assignment[Assignment.FINAL_SCORE] and not assignment[Assignment.CONFLICTS]:
                    alternates_by_forum[paper_note.id].append(assignment)
        num_alternates = int(self.config[Configuration.ALTERNATES]) if self.config[Configuration.ALTERNATES] else 10
        for forum, alternates in alternates_by_forum.items():
            alternates_by_forum[forum] = sorted(alternates, key=lambda a: a[Assignment.FINAL_SCORE], reverse=True)[0:num_alternates]

        return dict(assignments_by_forum), dict(alternates_by_forum)


