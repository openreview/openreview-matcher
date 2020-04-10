'''
Responsible for:
1) encoding OpenReview objects into a compatible format for the matcher.
2) decoding the result of the matcher and translating into OpenReview objects.
'''

from collections import defaultdict, namedtuple
import numpy as np
import logging

def _score_to_cost(score, scaling_factor=100):
    '''
    Simple helper function for converting a score into a cost.

    Scaling factor is arbitrary and usually shouldn't be changed.
    '''
    return score * -scaling_factor

class EncoderError(Exception):
    '''Exception wrapper class for errors related to Encoder'''
    pass

class Encoder:
    '''
    Responsible for keeping track of paper and reviewer indexes.

    Arguments:
    - `reviewers`:
        a list of IDs, each representing a reviewer.

    - `papers`:
        a list of IDs, each representing a paper.

    - `constraints`:
        a list of triples, formatted as follows:
        (<str paper_ID>, <str reviewer_ID>, <int [-1, 0, or 1]>)

    - `scores_by_type`:
        a dict, keyed on string IDs representing score 'types',
        where each value is a list of triples, formatted as follows:
        (<str paper_ID>, <str reviewer_ID>, <float score>)

   - `weight_by_type`:
        a dict, keyed on string IDs that match those in `scores_by_type`,
        where each value is a float, indicating the relative weight of the corresponding
        score type.

    - `normalization_types`:
        an array of score types where we need to apply normalization.

    '''
    def __init__(
            self,
            reviewers,
            papers,
            constraints,
            scores_by_type,
            weight_by_type,
            normalization_types=[],
            logger=logging.getLogger(__name__)
        ):
        self.logger = logger

        self.reviewers = reviewers
        self.papers = papers

        self.index_by_user = {r: i for i, r in enumerate(self.reviewers)}
        self.index_by_forum = {n: i for i, n in enumerate(self.papers)}

        self.logger.debug('Init encoding')
        self.logger.info('Use normalization={}'.format(normalization_types))

        self.matrix_shape = (
            len(self.papers),
            len(self.reviewers)
        )

        self.score_matrices = {
            score_type: self._encode_scores(scores) for score_type, scores in scores_by_type.items()
        }

        with_normalization_matrices = {}
        without_normalization_matrices = {}

        for score_type, scores in self.score_matrices.items():
            if score_type in normalization_types:
                with_normalization_matrices[score_type] = scores
            else:
                without_normalization_matrices[score_type] = scores

        self.constraint_matrix = self._encode_constraints(constraints)

        # don't use numpy.sum() here. it will collapse the matrices into a single value.
        self.aggregate_score_matrix = np.full(self.matrix_shape, 0, dtype=float)

        if without_normalization_matrices:
            self.aggregate_score_matrix = sum([
                scores * weight_by_type[score_type] for score_type, scores in without_normalization_matrices.items()
            ])

        if with_normalization_matrices:
            self.aggregate_score_matrix += self._normalize(weight_by_type, with_normalization_matrices)

        self.cost_matrix = _score_to_cost(self.aggregate_score_matrix)

    def _normalize(self, weight_by_type, with_normalization_matrices):

        indicator = { score_type: scores != 0.0  for score_type, scores in with_normalization_matrices.items() }
        sum_of_weights = sum([
            indicator * weight_by_type[score_type] for score_type, indicator in indicator.items()
        ])
        normalizer = np.where(sum_of_weights == 0, 0, 1/sum_of_weights)

        return (normalizer * sum([
            scores * weight_by_type[score_type] for score_type, scores in with_normalization_matrices.items()
        ]))

    def _encode_scores(self, scores):
        '''return a matrix containing unweighted scores.'''
        default = scores.get('default', 0)
        edges = scores.get('edges', [])
        score_matrix = np.full(self.matrix_shape, default, dtype=float)

        for forum, user, score in edges:
            coordinates = (self.index_by_forum[forum], self.index_by_user[user])
            score_matrix[coordinates] = score

        return score_matrix

    def _encode_constraints(self, constraints):
        '''
        return a matrix containing constraint values. label should have no bearing on the outcome.
        '''
        constraint_matrix = np.full(self.matrix_shape, 0, dtype=int)
        for forum, user, constraint in constraints:
            coordinates = (self.index_by_forum[forum], self.index_by_user[user])
            constraint_matrix[coordinates] = constraint

        return constraint_matrix

    def decode_assignments(self, flow_matrix):
        '''
        Return a dictionary, keyed on forum IDs, with lists containing dicts
        representing assigned users.
        '''
        assignments_by_forum = defaultdict(list)

        for paper_index, paper_flows in enumerate(flow_matrix):
            paper_id = self.papers[paper_index]
            for reviewer_index, flow in enumerate(paper_flows):
                reviewer = self.reviewers[reviewer_index]

                if flow:
                    coordinates = (paper_index, reviewer_index)
                    paper_user_entry = {
                        'aggregate_score': self.aggregate_score_matrix[coordinates],
                        'user': reviewer
                    }
                    assignments_by_forum[paper_id].append(paper_user_entry)

        return dict(assignments_by_forum)

    def decode_alternates(self, flow_matrix, num_alternates):
        '''
        Return a dictionary, keyed on forum IDs, with lists containing dicts
        representing alternate suggested users.

        '''
        alternates_by_forum = {}

        for paper_index, paper_flows in enumerate(flow_matrix):
            paper_id = self.papers[paper_index]
            unassigned = []
            for reviewer_index, flow in enumerate(paper_flows):
                reviewer = self.reviewers[reviewer_index]

                # alternates must not be assigned
                if not flow:
                    coordinates = (paper_index, reviewer_index)
                    paper_user_entry = {
                        'aggregate_score': self.aggregate_score_matrix[coordinates],
                        'user': reviewer
                    }
                    unassigned.append(paper_user_entry)

            unassigned.sort(key=lambda entry: entry['aggregate_score'], reverse=True)

            alternates_by_forum[paper_id] = unassigned[:num_alternates]

        return alternates_by_forum
