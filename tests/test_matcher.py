'''
Verifies that custom loads are being used correctly in the matcher.

'''

from collections import defaultdict, namedtuple
import itertools

import pytest
import numpy as np

from matcher.matcher_client import MatcherClientMock
from matcher.matcher import Matcher

MockNote = namedtuple('Note', ['id', 'forum', 'index'])
MockEdge = namedtuple('Edge', ['head', 'tail', 'weight', 'label'])
MockReviewer = namedtuple('Reviewer', ['id', 'index'])

H = 10.0
M = 3.0

@pytest.fixture
def matcher_context():
    '''test fixture for matcher tests'''

    num_papers = 3
    num_reviewers = 4

    score_matrix = np.array([
        [H, 0, 0, 0],
        [H, 0, 0, 0],
        [H, 0, 0, 0]
    ])

    config = {
        'alternates': 3,
        'max_users': 1,
        'max_papers': 3,
        'min_papers': 0,
        'scores_specification': {
            'mock/-/score_edge': {
                'weight': 1,
                'default': 0
            }
        }
    }

    papers = [MockNote(id=i, forum=i, index=i) for i in range(num_papers)]
    reviewers = [MockReviewer(id='reviewer{}'.format(i), index=i) for i in range(num_reviewers)]

    edges_by_invitation = {
        'mock/-/score_edge': [
            MockEdge(
                head=note.forum,
                tail=reviewer.id,
                weight=score_matrix[note.index, reviewer.index],
                label='') \
            for note, reviewer in itertools.product(papers, reviewers)
        ]
    }

    yield papers, reviewers, edges_by_invitation, config


def test_matcher_custom_load_negative(matcher_context):
    '''
    Reviewer 0 has a custom load of -9.4, and high scores across the board.

    Custom load should be treated as 0. Reviewer 0 should not be assigned any papers.
    '''
    papers, reviewers, edges_by_invitation, config = matcher_context

    # set a negative custom load for reviewer0.
    # they should be assigned zero papers.
    custom_load_edges = [MockEdge(head=0, tail='reviewer0', weight=-9.4, label='')]

    mock_client = MatcherClientMock(
        reviewers=[r.id for r in reviewers],
        papers=papers,
        edges_by_invitation=edges_by_invitation,
        custom_load_edges=custom_load_edges
    )

    matcher = Matcher(mock_client, config)
    matcher.compute_match()

    assert matcher.solution.any()

    # reviewer0 (axis 1) should have no assignments at all, despite high scores.
    assert sum(matcher.solution[:, 0]) == 0

def test_matcher_custom_load_one(matcher_context):
    '''
    Reviewer 0 should have no more than 1 assignment.
    '''
    papers, reviewers, edges_by_invitation, config = matcher_context

    # set a custom load of 1 for reviewer0.
    # they should be assigned 1 paper.
    custom_load_edges = [MockEdge(head=0, tail='reviewer0', weight=1, label='')]

    mock_client = MatcherClientMock(
        reviewers=[r.id for r in reviewers],
        papers=papers,
        edges_by_invitation=edges_by_invitation,
        custom_load_edges=custom_load_edges
    )

    matcher = Matcher(mock_client, config)
    matcher.compute_match()

    assert matcher.solution.any()

    # reviewer0 (axis 1) should have at most 1 assignment
    assert sum(matcher.solution[:, 0]) <= 1

def test_matcher_custom_overload(matcher_context):
    '''
    Default maximum number of assignments per reviewer is 1,
    but reviewer 3 has a custom load of 3.

    All assignments should be given to reviewer 3, and none should be given to the others.
    '''
    papers, reviewers, edges_by_invitation, config = matcher_context

    # set a custom load of 3 for reviewer0, despite default 'max_papers' value of 1.
    config['max_papers'] = 1
    custom_load_edges = [MockEdge(head=0, tail='reviewer0', weight=3, label='')]

    mock_client = MatcherClientMock(
        reviewers=[r.id for r in reviewers],
        papers=papers,
        edges_by_invitation=edges_by_invitation,
        custom_load_edges=custom_load_edges
    )

    matcher = Matcher(mock_client, config)
    matcher.compute_match()

    assert matcher.solution.any()

    # reviewer0 (axis 1) should have 3 assignments, despite max_papers=1
    assert sum(matcher.solution[:, 0]) == 3
