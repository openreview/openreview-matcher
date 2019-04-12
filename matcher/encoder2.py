from collections import defaultdict
import numpy as np
import logging
import time

from matcher.CostFunction import CostFunction
from matcher.fields import Configuration
from matcher.fields import PaperReviewerScore
from matcher.fields import Assignment


class Encoder2:


    def __init__(self, metadata=None, config=None, reviewers=None, cost_func=CostFunction(), logger=logging.getLogger(__name__)):
        self.logger = logger
        self.logger.debug("Using Encoder2")
        self.metadata = metadata
        self.config = config
        self._cost_func = cost_func

        self._cost_matrix = np.zeros((0, 0))
        self.constraint_matrix = np.zeros((0, 0))
        self.score_names = config[Configuration.SCORES_NAMES]
        self._weights = self._get_weight_dict(config[Configuration.SCORES_NAMES], config[Configuration.SCORES_WEIGHTS])
        self.constraints = config.get(Configuration.CONSTRAINTS,{})

        if self.metadata and self.config and self.metadata.reviewers and self.metadata.paper_notes:
            self.encode()

    def _get_weight_dict (self, names, weights):
        return dict(zip(names, [ float(w) for w in weights]))

    @property
    def cost_function (self):
        return self._cost_func

    @property
    def cost_matrix (self):
        return self._cost_matrix

    @property
    def weights (self):
        return self._weights

    def _update_cost_matrix (self, entry, reviewer_index, paper_index):
        coordinates = reviewer_index, paper_index
        if entry:
            self._cost_matrix[coordinates] = self.cost_function.cost(entry, self.weights)
            if entry.get(PaperReviewerScore.CONFLICTS):
                self.constraint_matrix[coordinates] = -1
            else:
                self.constraint_matrix[coordinates] = 0

    # The entry may contain constraints ('+inf'/ '-inf') and/or conflicts
    # Rules:
    # 1.  If constraint == LOCK set the matrix cell to 1
    # 2.  If constraint == VETO or conflict set the matrix cell to -1
    def _update_constraint_matrix (self, entry, reviewer_index, paper_index):
        coordinates = reviewer_index, paper_index
        constraint = entry.get('constraint')
        conflict = entry.get('conflicts')
        if constraint and constraint == Configuration.LOCK:
            self.constraint_matrix[coordinates] = 1
        elif constraint or conflict:
            self.constraint_matrix[coordinates] = -1

    def validate (self, reviewer, forum_id, entry):
        md_note = self.metadata_note_map[forum_id]
        for e in md_note.content['entries']:
            if e['userid'] == reviewer:
                scores = e['scores']
                assert self.cost_function.cost(scores,self.weights) == self.cost_function.cost(entry, self.weights)



    def encode (self):
        self.logger.debug("Encoding")
        now = time.time()
        self._cost_matrix = np.zeros((len(self.metadata.reviewers), len(self.metadata.paper_notes)))
        self.constraint_matrix = np.zeros(np.shape(self._cost_matrix))
        for reviewer_index, reviewer in enumerate(self.metadata.reviewers):
            for paper_index, paper_note in enumerate(self.metadata.paper_notes):
                entry = self.metadata.get_entry(paper_note.id, reviewer)
                # self.validate(reviewer,paper_note.id,entry)
                self._update_cost_matrix(entry, reviewer_index, paper_index)
                self._update_constraint_matrix(entry, reviewer_index, paper_index)
        self.logger.debug("Done encoding.  Took {}".format(time.time() - now))


    def decode (self, flow_matrix):
        now = time.time()
        self.logger.debug("Decoding")
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
                    assignment[Assignment.SCORES] = self.cost_function.weight_scores(entry, self.weights)
                    assignment[Assignment.CONFLICTS] = entry.get(PaperReviewerScore.CONFLICTS)
                    assignment[Assignment.FINAL_SCORE] = self.cost_function.aggregate_score(entry, self.weights)

                if flow:
                    assignments_by_forum[paper_note.id].append(assignment)
                elif assignment[Assignment.FINAL_SCORE] and not assignment[Assignment.CONFLICTS]:
                    alternates_by_forum[paper_note.id].append(assignment)
        num_alternates = int(self.config[Configuration.ALTERNATES]) if self.config[Configuration.ALTERNATES] else 10
        for forum, alternates in alternates_by_forum.items():
            alternates_by_forum[forum] = sorted(alternates, key=lambda a: a[Assignment.FINAL_SCORE], reverse=True)[0:num_alternates]
        self.logger.debug("Done decoding.  Took {}".format(time.time() - now))
        return dict(assignments_by_forum), dict(alternates_by_forum)


