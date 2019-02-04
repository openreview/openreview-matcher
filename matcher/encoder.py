from collections import defaultdict
import numpy as np

from . import utils
from matcher.fields import Configuration
from matcher.fields import PaperReviewerScore
from matcher.fields import Assignment


class Encoder(object):


    def __init__(self, metadata=None, config=None, reviewer_ids=None, cost_func=utils.cost):

        self.metadata = []
        self.config = {}
        self.reviewer_ids = []
        self.cost = cost_func

        self.cost_matrix = np.zeros((0, 0))
        self.constraint_matrix = np.zeros((0, 0))
        self.entries_by_forum = {}
        self.index_by_forum = {}
        self.index_by_reviewer = {}
        self.forum_by_index = {}
        self.reviewer_by_index = {}
        self.score_names = config[Configuration.SCORES_NAMES] # a list of score names
        self.weights = self._get_weight_dict(config[Configuration.SCORES_NAMES], config[Configuration.SCORES_WEIGHTS] )
        self.constraints = config.get(Configuration.CONSTRAINTS,{})

        if metadata and config and reviewer_ids:
            self.encode(metadata, config, reviewer_ids, cost_func)

    def _get_weight_dict (self, names, weights):
        return dict(zip(names, [ float(w) for w in weights]))

    def _error_check_scores (self, entry, prs_note_id, valid_score_names):
        for k in entry['scores']:
            assert k in valid_score_names, \
            "The entry in the note id={} has a score name ({}) that isn't in the config".format(prs_note_id, k)

    def encode(self, metadata, config, reviewer_ids, cost_func):
        '''
        Encodes the cost and constraint matrices to be used by the solver.

        metadata    = a list of metadata Notes
        weights     = a dict of weights keyed on score type
          e.g. { 'tpms': 0.5, 'bid': 1.0, 'recommendation': 2.0 }
        reviewers   = a list of reviewer IDs (to lookup in metadata entries)

        '''
        self.metadata = metadata
        self.config = config
        self.reviewer_ids = reviewer_ids
        self.cost_func = cost_func

        self.cost_matrix = np.zeros((len(self.reviewer_ids), len(self.metadata)))
        self.constraint_matrix = np.zeros(np.shape(self.cost_matrix))

        self.entries_by_forum = {m.forum: {entry[PaperReviewerScore.USERID]: entry
                                           for entry in m.content[PaperReviewerScore.ENTRIES]}
                                 for m in self.metadata}

        self.index_by_forum = {m.forum: index
                               for index, m in enumerate(self.metadata)}

        self.index_by_reviewer = {r: index
                                  for index, r in enumerate(self.reviewer_ids)}

        self.forum_by_index = {index: forum
                               for forum, index in self.index_by_forum.items()}

        self.reviewer_by_index = {index: id
                                  for id, index in self.index_by_reviewer.items()}

        self.constraints = config.get(Configuration.CONSTRAINTS,{})

        for forum, entry_by_id in self.entries_by_forum.items():
            paper_index = self.index_by_forum[forum]

            for id, reviewer_index in self.index_by_reviewer.items():
                # first check the metadata entry for scores and conflicts
                coordinates = reviewer_index, paper_index
                entry = entry_by_id.get(id)
                if entry:
                    # Check that the scores in the entry have same names as those in the config note
                    self._error_check_scores(entry, self.metadata[paper_index], self.score_names)
                    self.cost_matrix[coordinates] = self.cost_func(entry[PaperReviewerScore.SCORES], self.weights)
                    if entry.get(PaperReviewerScore.CONFLICTS):
                        self.constraint_matrix[coordinates] = -1
                    else:
                        self.constraint_matrix[coordinates] = 0

                # overwrite constraints with user-added constraints found in config
                user_constraint = self.constraints.get(forum, {}).get(id)
                if user_constraint:
                    if '-inf' in user_constraint:
                        self.constraint_matrix[coordinates] = -1
                    if '+inf' in user_constraint:
                        self.constraint_matrix[coordinates] = 1

    def decode(self, solution):
        '''
        Decodes a solution into assignments
        '''
        flow_matrix = solution

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
                    assignment[Assignment.SCORES] = utils.weight_scores(entry.get(PaperReviewerScore.SCORES), self.weights)
                    assignment[Assignment.CONFLICTS] = entry.get(PaperReviewerScore.CONFLICTS)
                    assignment[Assignment.FINAL_SCORE] = utils.safe_sum(
                        utils.weight_scores(entry.get(PaperReviewerScore.SCORES), self.weights).values())

                if flow:
                    assignments_by_forum[forum].append(assignment)
                elif assignment[Assignment.FINAL_SCORE] and not assignment[Assignment.CONFLICTS]:
                    alternates_by_forum[forum].append(assignment)
        num_alternates = int(self.config[Configuration.ALTERNATES]) if self.config[Configuration.ALTERNATES] else 10
        for forum, alternates in alternates_by_forum.items():
            alternates_by_forum[forum] = sorted(alternates, key=lambda a: a[Assignment.FINAL_SCORE], reverse=True)[0:num_alternates]

        return dict(assignments_by_forum), dict(alternates_by_forum)
