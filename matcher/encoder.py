'''
Responsible for:
1) encoding OpenReview objects into a compatible format for the matcher.
2) decoding the result of the matcher and translating into OpenReview objects.
'''

from collections import defaultdict, namedtuple
import numpy as np

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
            normalization_types=[]
        ):
        print('Use normalization', normalization_types)

        self.reviewers = reviewers
        self.papers = papers

        self.index_by_user = {r: i for i, r in enumerate(self.reviewers)}
        self.index_by_forum = {n: i for i, n in enumerate(self.papers)}

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


    def _encode_scores(self, scores, default=0):
        '''return a matrix containing unweighted scores.'''
        score_matrix = np.full(self.matrix_shape, default, dtype=float)

        for forum, user, score in scores:
            if not isinstance(score, float) and not isinstance(score, int):
                try:
                    score = float(score)
                except ValueError:
                    raise EncoderError(
                        'could not convert score {} of type {} to float ({}, {})'.format(
                            score, type(score), forum, user))

            # sometimes papers or reviewers get deleted after edges are created,
            # so we need to check that the head/tail are still valid
            if forum in self.papers and user in self.reviewers:
                coordinates = (self.index_by_forum[forum], self.index_by_user[user])
                score_matrix[coordinates] = score

        return score_matrix

    def _encode_constraints(self, constraints):
        '''
        return a matrix containing constraint values. label should have no bearing on the outcome.
        '''
        constraint_matrix = np.full(self.matrix_shape, 0, dtype=int)
        for forum, user, constraint in constraints:
            if not isinstance(constraint, float) and not isinstance(constraint, int):
                try:
                    constraint = int(constraint)
                except ValueError:
                    raise EncoderError(
                        'could not convert constraint {} of type {} to int ({}, {})'.format(
                            constraint, type(constraint), forum, user))

            if not constraint in [-1, 0, 1]:
                raise ValueError(
                    'constraint {} ({}, {}) must be an int of value -1, 0, or 1'.format(
                        constraint, forum, user))

            # sometimes papers or reviewers get deleted after constraint_edges are created,
            # so we need to check that the head/tail are still valid
            if forum in self.papers and user in self.reviewers:
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
