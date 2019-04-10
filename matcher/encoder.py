import time
from collections import defaultdict
import numpy as np
import logging

from matcher.CostFunction import CostFunction
from matcher.fields import Configuration
from matcher.fields import PaperReviewerScore
from matcher.fields import Assignment


class Encoder(object):


    def __init__(self, metadata=None, config=None, reviewer_ids=[], cost_func=CostFunction(), logger=logging.getLogger(__name__)):
        self.logger = logger
        self.logger.debug("Using Encoder")
        self.metadata = metadata
        self.config = config
        self.reviewer_ids = reviewer_ids
        self._cost_func = cost_func

        self._cost_matrix = np.zeros((0, 0))
        self.constraint_matrix = np.zeros((0, 0))
        self.entries_by_forum = {}
        self.index_by_forum = {}
        self.index_by_reviewer = {}
        self.forum_by_index = {}
        self.reviewer_by_index = {}
        self.score_edge_invitations = config[Configuration.SCORES_INVITATIONS]
        self.score_names = config[Configuration.SCORES_NAMES] # a list of score names
        self.weights = self._get_weight_dict(config[Configuration.SCORES_NAMES], config[Configuration.SCORES_WEIGHTS] )
        self.constraints = config.get(Configuration.CONSTRAINTS,{})

        if self.metadata and self.config and self.reviewer_ids:
            self._error_check_scores()
            self.encode()

    @property
    def cost_matrix (self):
        return self._cost_matrix

    @property
    def cost_function (self):
        return self._cost_func

    def _get_weight_dict (self, names, weights):
        return dict(zip(names, [ float(w) for w in weights]))

    def _error_check_scores (self):
        assert len(self.score_edge_invitations) == len(self.score_names) == len(self.weights.keys()), "The configuration note should specify the same number of scores, weights, and score-invitations"

    def encode(self):
        '''
        Encodes the cost and constraint matrices to be used by the solver.
        weights     = a dict of weights keyed on score type
          e.g. { 'tpms': 0.5, 'bid': 1.0, 'recommendation': 2.0 }

        '''
        self.logger.debug("Encoding")
        now = time.time()

        self._cost_matrix = np.zeros((len(self.reviewer_ids), self.metadata.len()))
        self.constraint_matrix = np.zeros(np.shape(self._cost_matrix))

        self.entries_by_forum  = self.metadata.entries_by_forum_map

        self.index_by_forum = {m.id: index
                               for index, m in enumerate(self.metadata.paper_notes)}

        self.index_by_reviewer = {r: index
                                  for index, r in enumerate(self.reviewer_ids)}

        self.forum_by_index = {index: forum
                               for forum, index in self.index_by_forum.items()}

        self.reviewer_by_index = {index: id
                                  for id, index in self.index_by_reviewer.items()}

        self.constraints = self.config.get(Configuration.CONSTRAINTS,{})

        for forum, entry_by_userid in self.entries_by_forum.items():
            paper_index = self.index_by_forum[forum]

            for id, reviewer_index in self.index_by_reviewer.items():
                # first check the metadata entry for scores and conflicts
                coordinates = reviewer_index, paper_index
                entry = entry_by_userid.get(id)
                if entry:

                    self._cost_matrix[coordinates] = self.cost_function.cost(entry, self.weights)
                    if entry.get(PaperReviewerScore.CONFLICTS):
                        self.constraint_matrix[coordinates] = -1
                    else:
                        self.constraint_matrix[coordinates] = 0

                # overwrite constraints with user-added constraints found in config
                user_constraint = self.constraints.get(forum, {}).get(id)
                if user_constraint:
                    if Configuration.VETO in user_constraint:
                        self.constraint_matrix[coordinates] = -1
                    if Configuration.LOCK in user_constraint:
                        self.constraint_matrix[coordinates] = 1

        self.logger.debug("Done encoding.  Took {}".format(time.time() - now))


    def decode(self, solution):
        '''
        Decodes a solution into assignments
        '''
        flow_matrix = solution
        now = time.time()
        self.logger.debug("Decoding")
        assignments_by_forum = defaultdict(list)
        alternates_by_forum = defaultdict(list)
        for reviewer_index, reviewer_flows in enumerate(flow_matrix):
            user_id = self.reviewer_by_index[reviewer_index]

            for paper_index, flow in enumerate(reviewer_flows):
                forum = self.forum_by_index[paper_index]

                assignment = {
                    Assignment.USERID: user_id,
                    Assignment.SCORES: {},
                    Assignment.CONFLICTS: [],
                    Assignment.FINAL_SCORE: None
                }
                entry = self.entries_by_forum[forum].get(user_id)

                if entry:
                    # assignment[Assignment.SCORES] = utils.weight_scores(entry.get(PaperReviewerScore.SCORES), self.weights)
                    assignment[Assignment.SCORES] = self.cost_function.weight_scores(entry, self.weights)
                    assignment[Assignment.CONFLICTS] = entry.get(PaperReviewerScore.CONFLICTS)
                    assignment[Assignment.FINAL_SCORE] = self.cost_function.aggregate_score(entry, self.weights)

                if flow:
                    assignments_by_forum[forum].append(assignment)
                elif assignment[Assignment.FINAL_SCORE] and not assignment[Assignment.CONFLICTS]:
                    alternates_by_forum[forum].append(assignment)
        num_alternates = int(self.config[Configuration.ALTERNATES]) if self.config[Configuration.ALTERNATES] else 10
        for forum, alternates in alternates_by_forum.items():
            alternates_by_forum[forum] = sorted(alternates, key=lambda a: a[Assignment.FINAL_SCORE], reverse=True)[0:num_alternates]
        self.logger.debug("Done decoding.  Took {}".format(time.time() - now))
        return dict(assignments_by_forum), dict(alternates_by_forum)
