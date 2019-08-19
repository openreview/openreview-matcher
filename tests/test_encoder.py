'''
Unit test suite for `matcher/encoder.py`
'''


import itertools
from collections import namedtuple

import pytest
import numpy as np

from matcher.encoder import Encoder

MockNote = namedtuple('Note', ['id', 'forum'])
MockEdge = namedtuple('Edge', ['head', 'tail', 'weight', 'label'])

@pytest.fixture
def encoder_context():
    '''pytest fixture for Encoder testing'''
    num_reviewers = 4
    num_papers = 3

    papers = [MockNote(id=i, forum=i) for i in range(num_papers)]
    reviewers = ['reviewer{}'.format(i) for i in range(num_reviewers)]

    matrix_shape = (num_papers, num_reviewers)

    return papers, reviewers, matrix_shape

def test_encoder_basic(encoder_context):
    '''Basic test of Encoder functionality, without constraints.'''
    papers, reviewers, matrix_shape = encoder_context

    edges_by_invitation = {
        'mock/-/score_edge': [
            MockEdge(head=note.forum, tail=reviewer, weight=0.5, label='') \
            for note, reviewer in itertools.product(papers, reviewers)
        ],
        'mock/-/bid_edge': [
            MockEdge(head=note.forum, tail=reviewer, weight=None, label='mock_bid') \
            for note, reviewer in itertools.product(papers, reviewers)
        ]
    }

    scores_specification = {
        'mock/-/bid_edge': {
            'weight': 1,
            'default': 0,
            'translate_map': {
                'mock_bid': 1
            }
        },
        'mock/-/score_edge': {
            'weight': 1,
            'default': 0
        }
    }

    constraint_edges = []

    encoder = Encoder(
        reviewers,
        papers,
        constraint_edges,
        edges_by_invitation,
        scores_specification)

    # all values in the bids matrix should be 1.0
    encoded_bid_matrix = encoder.score_matrices['mock/-/bid_edge']
    correct_bid_matrix = np.ones(matrix_shape)
    assert encoded_bid_matrix.shape == correct_bid_matrix.shape
    assert (encoded_bid_matrix == correct_bid_matrix).all()

    # all values in the score matrix should be 0.5
    encoded_score_matrix = encoder.score_matrices['mock/-/score_edge']
    correct_score_matrix = np.full(matrix_shape, 0.5, dtype=float)
    assert encoded_score_matrix.shape == correct_score_matrix.shape
    assert (encoded_score_matrix == correct_score_matrix).all()

    mock_solution = np.asarray([
        [1, 0, 0, 0],
        [0, 1, 0, 1],
        [0, 0, 1, 0]
    ])

    assignments_by_forum = encoder.assignments(mock_solution)

    paper0_assigned = [entry.user for entry in assignments_by_forum[0]]
    paper1_assigned = [entry.user for entry in assignments_by_forum[1]]
    paper2_assigned = [entry.user for entry in assignments_by_forum[2]]

    assert len(paper0_assigned) == 1
    assert len(paper1_assigned) == 2
    assert len(paper2_assigned) == 1

    # only test that a reviewer is in the list of assigned, not the order.
    assert 'reviewer0' in paper0_assigned
    assert 'reviewer1' in paper1_assigned
    assert 'reviewer2' in paper2_assigned
    assert 'reviewer3' in paper1_assigned

    alternates_by_forum = encoder.alternates(mock_solution, 3)

    paper0_alternates = [entry.user for entry in alternates_by_forum[0]]
    paper1_alternates = [entry.user for entry in alternates_by_forum[1]]
    paper2_alternates = [entry.user for entry in alternates_by_forum[2]]

    assert len(paper0_alternates) == 3
    assert len(paper1_alternates) == 2
    assert len(paper2_alternates) == 3

    # only test that the assigned reviewer is *not* in the list of alternates.
    assert 'reviewer0' not in paper0_alternates
    assert 'reviewer1' not in paper1_alternates
    assert 'reviewer2' not in paper2_alternates
    assert 'reviewer3' not in paper1_alternates

def test_encoder_weighting(encoder_context):
    '''Ensure that matrix weights are applied properly'''
    papers, reviewers, matrix_shape = encoder_context

    edges_by_invitation = {
        'mock/-/score_edge': [
            MockEdge(head=note.forum, tail=reviewer, weight=0.5, label='') \
            for note, reviewer in itertools.product(papers, reviewers)
        ],
        'mock/-/bid_edge': [
            MockEdge(head=note.forum, tail=reviewer, weight=None, label='mock_bid') \
            for note, reviewer in itertools.product(papers, reviewers)
        ],
        'mock/-/recommendation': [
            MockEdge(head=note.forum, tail=reviewer, weight=None, label='recommended') \
            for note, reviewer in itertools.product(papers, reviewers)
        ]
    }

    scores_specification = {
        'mock/-/score_edge': {
            'weight': -20,
            'default': 0
        },
        'mock/-/bid_edge': {
            'weight': 1.5,
            'default': 0,
            'translate_map': {
                'mock_bid': 1
            }
        },
        'mock/-/recommendation': {
            'weight': 0.5,
            'default': 0,
            'translate_map': {
                'recommended': 5
            }
        }
    }

    constraint_edges = []

    encoder = Encoder(
        reviewers,
        papers,
        constraint_edges,
        edges_by_invitation,
        scores_specification)

    # all values in the score matrix should be 0.5, because they're unweighted
    encoded_score_matrix = encoder.score_matrices['mock/-/score_edge']
    correct_score_matrix = np.full(matrix_shape, 0.5, dtype=float)
    assert encoded_score_matrix.shape == correct_score_matrix.shape
    assert (encoded_score_matrix == correct_score_matrix).all()

    # all values in the bids matrix should be 1.0, because they're unweighted
    encoded_bid_matrix = encoder.score_matrices['mock/-/bid_edge']
    correct_bid_matrix = np.full(matrix_shape, 1.0, dtype=float)
    assert encoded_bid_matrix.shape == correct_bid_matrix.shape
    assert (encoded_bid_matrix == correct_bid_matrix).all()

    # all values in the recommendations matrix should be 5, because they're unweighted
    encoded_recommendations_matrix = encoder.score_matrices['mock/-/recommendation']
    correct_recommendations_matrix = np.full(matrix_shape, 5, dtype=float)
    assert encoded_recommendations_matrix.shape == correct_recommendations_matrix.shape
    assert (encoded_recommendations_matrix == correct_recommendations_matrix).all()

    # all values in the aggregate score matrix should be:
    #   (0.5 * -20) + (1.0 * 1.5) + (5 * 0.5) = -6.0
    encoded_aggregate_matrix = encoder.aggregate_score_matrix
    correct_aggregate_matrix = np.full(matrix_shape, -6.0, dtype=float)
    assert encoded_aggregate_matrix.shape == correct_aggregate_matrix.shape
    assert (encoded_aggregate_matrix == correct_aggregate_matrix).all()

def test_encoder_defaults(encoder_context):
    '''ensure the default values are being encoded properly'''

    papers, reviewers, matrix_shape = encoder_context

    edges_by_invitation = {
        'mock/-/score_edge': [
            MockEdge(head=note.forum, tail=reviewer, weight=1, label='') \
            for note, reviewer in itertools.product(papers, reviewers)
        ],
        'mock/-/bid_edge': []
    }

    scores_specification = {
        'mock/-/score_edge': {
            'weight': 1,
            'default': 0
        },
        'mock/-/bid_edge': {
            'weight': 1,
            'default': -100,
            'translate_map': {
                'mock_bid': 1
            }
        }
    }

    constraint_edges = []

    encoder = Encoder(
        reviewers,
        papers,
        constraint_edges,
        edges_by_invitation,
        scores_specification)

    # all values in the score matrix should be 1.0, because they're unweighted
    encoded_score_matrix = encoder.score_matrices['mock/-/score_edge']
    correct_score_matrix = np.full(matrix_shape, 1.0, dtype=float)
    assert encoded_score_matrix.shape == correct_score_matrix.shape
    assert (encoded_score_matrix == correct_score_matrix).all()

    # all values in the bids matrix should be -100, because that's the weighted default value
    encoded_bid_matrix = encoder.score_matrices['mock/-/bid_edge']
    correct_bid_matrix = np.full(matrix_shape, -100, dtype=float)
    assert encoded_bid_matrix.shape == correct_bid_matrix.shape
    assert (encoded_bid_matrix == correct_bid_matrix).all()

    # all values in the aggregate score matrix should be:
    #   (1.0 * 1.0) + (-100 * 1.0) = -99
    encoded_aggregate_matrix = encoder.aggregate_score_matrix
    correct_aggregate_matrix = np.full(matrix_shape, -99, dtype=float)
    assert encoded_aggregate_matrix.shape == correct_aggregate_matrix.shape
    assert (encoded_aggregate_matrix == correct_aggregate_matrix).all()

def test_encoder_constraints(encoder_context):
    '''Ensure that constraints are being encoded properly'''
    papers, reviewers, matrix_shape = encoder_context

    # computing constraints is completely separate from computing scores,
    # so we don't test them here.
    edges_by_invitation = {}
    scores_specification = {}


    # label should have no bearing on the outcome
    # any positive weight should be encoded as 1
    # any negative weight should be encoded as -1
    # any zero weight should be encoded as 0
    constraint_edges = [
        MockEdge(head=0, tail='reviewer0', weight=0, label='neutral'),
        MockEdge(head=1, tail='reviewer0', weight=1, label='no conflict'),
        MockEdge(head=2, tail='reviewer0', weight=-0.001, label='yes conflict'),
        MockEdge(head=0, tail='reviewer1', weight=0.66, label='bad conflict'),
    ]

    encoder = Encoder(
        reviewers,
        papers,
        constraint_edges,
        edges_by_invitation,
        scores_specification
    )

    correct_constraint_matrix = np.full(matrix_shape, 0, dtype=int)
    correct_constraint_matrix[0][0] = 0
    correct_constraint_matrix[1][0] = 1
    correct_constraint_matrix[2][0] = -1
    correct_constraint_matrix[0][1] = 1

    encoded_constraint_matrix = encoder.constraint_matrix
    assert encoded_constraint_matrix.shape == correct_constraint_matrix.shape
    assert (encoded_constraint_matrix == correct_constraint_matrix).all()
