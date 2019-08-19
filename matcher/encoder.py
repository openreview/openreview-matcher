'''
Responsible for:
1) encoding OpenReview objects into a compatible format for the matcher.
2) decoding the result of the matcher and translating into OpenReview objects.
'''

from collections import defaultdict, namedtuple
import numpy as np

PaperUserEntry = namedtuple('PaperUserEntry', ['aggregate_score', 'user'])

class EncoderError(Exception):
    '''Exception wrapper class for errors related to Encoder'''
    pass

class Encoder:
    '''Responsible for keeping track of paper and reviewer indexes.'''
    def __init__(
            self,
            reviewers,
            papers,
            constraint_edges,
            edges_by_invitation,
            score_spec
        ):

        self.reviewers = reviewers
        self.papers = papers

        self.index_by_user = {r: i for i, r in enumerate(self.reviewers)}
        self.index_by_forum = {n.forum: i for i, n in enumerate(self.papers)}

        self.matrix_shape = (
            len(self.papers),
            len(self.reviewers)
        )

        self.score_matrices = {
            inv: self._encode_edges(
                edges,
                default=score_spec[inv].get('default', 0),
                translate_map=score_spec[inv].get('translate_map')
            ) for inv, edges in edges_by_invitation.items()
        }

        self.constraint_matrix = self._encode_constraints(constraint_edges)

        # don't use numpy.sum() here. it will collapse the matrices into a single value.
        self.aggregate_score_matrix = sum([
            scores * score_spec[inv_id]['weight'] for inv_id, scores in self.score_matrices.items()
        ])

        self.cost_matrix = _score_to_cost(self.aggregate_score_matrix)


    def _encode_edges(self, edges, default=0, translate_map=None):
        '''return a matrix containing unweighted scores corresponding to those Edges.'''
        score_matrix = np.full(self.matrix_shape, default, dtype=float)

        for score_edge in edges:
            forum = score_edge.head
            user = score_edge.tail

            # sometimes papers or reviewers get deleted after edges are created,
            # so we need to check that the head/tail are still valid
            if forum in [n.forum for n in self.papers] and user in self.reviewers:
                coordinates = (self.index_by_forum[forum], self.index_by_user[user])
                score_matrix[coordinates] = _edge_to_score(score_edge, translate_map=translate_map)

        return score_matrix

    def _encode_constraints(self, constraint_edges):
        '''
        return a matrix containing constraint values. label should have no bearing on the outcome.

        any positive weight should be encoded as 1
        any negative weight should be encoded as -1
        any zero weight should be encoded as 0
        '''
        constraint_matrix = np.full(self.matrix_shape, 0, dtype=int)
        for constraint_edge in constraint_edges:
            forum = constraint_edge.head
            user = constraint_edge.tail

            # sometimes papers or reviewers get deleted after constraint_edges are created,
            # so we need to check that the head/tail are still valid
            if forum in [n.forum for n in self.papers] and user in self.reviewers:
                coordinates = (self.index_by_forum[forum], self.index_by_user[user])
                edge_weight = _edge_to_score(constraint_edge)
                if edge_weight > 0:
                    constraint_matrix[coordinates] = 1
                elif edge_weight < 0:
                    constraint_matrix[coordinates] = -1

        return constraint_matrix

    def assignments(self, flow_matrix):
        '''
        Return a dictionary, keyed on forum IDs, with lists containing PaperUserEntry objects
        representing assigned users.

        A `PaperUserEntry` is a simple namedtuple for holding reviewer ID and score(s).
        '''
        assignments_by_forum = defaultdict(list)

        for paper_index, paper_flows in enumerate(flow_matrix):
            paper_note = self.papers[paper_index]
            for reviewer_index, flow in enumerate(paper_flows):
                reviewer = self.reviewers[reviewer_index]

                if flow:
                    coordinates = (paper_index, reviewer_index)
                    paper_user_entry = PaperUserEntry(
                        aggregate_score=self.aggregate_score_matrix[coordinates],
                        user=reviewer
                    )
                    assignments_by_forum[paper_note.id].append(paper_user_entry)

        return dict(assignments_by_forum)

    def alternates(self, flow_matrix, num_alternates):
        '''
        Return a dictionary, keyed on forum IDs, with lists containing PaperUserEntry objects
        representing alternate suggested users.

        A `PaperUserEntry` is a simple namedtuple for holding reviewer ID and score(s).
        '''
        alternates_by_forum = {}

        for paper_index, paper_flows in enumerate(flow_matrix):
            paper_note = self.papers[paper_index]
            unassigned = []
            for reviewer_index, flow in enumerate(paper_flows):
                reviewer = self.reviewers[reviewer_index]

                # alternates must not be assigned
                if not flow:
                    coordinates = (paper_index, reviewer_index)
                    paper_user_entry = PaperUserEntry(
                        aggregate_score=self.aggregate_score_matrix[coordinates],
                        user=reviewer
                    )
                    unassigned.append(paper_user_entry)

            unassigned.sort(key=lambda entry: entry.aggregate_score, reverse=True)

            alternates_by_forum[paper_note.forum] = unassigned[:num_alternates]

        return alternates_by_forum

def _score_to_cost(score, scaling_factor=100):
    '''
    Simple helper function for converting a score into a cost.

    Scaling factor is arbitrary and usually shouldn't be changed.
    '''
    return score * -scaling_factor

def _edge_to_score(edge, translate_map=None):
    '''
    Given an openreview.Edge, and a mapping defined by `translate_map`,
    return a numeric score, given an Edge.

    '''

    score = edge.weight

    if translate_map:
        try:
            score = translate_map[edge.label]
        except KeyError:
            raise EncoderError(
                'Cannot translate label {} to score. Valid labels are: {}'.format(
                    edge.label, translate_map.keys()))

    if not isinstance(score, float) and not isinstance(score, int):
        try:
            score = float(score)
        except ValueError:
            raise EncoderError(
                'Edge {} has weight that is neither float nor int: {}, type {}'.format(
                    edge.id, edge.weight, type(edge.weight)))

    return score
