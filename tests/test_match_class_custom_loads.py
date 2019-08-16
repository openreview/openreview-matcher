'''
Verifies that custom loads are being used correctly in the matcher.

Each unit test uses the test_util fixture
to build a conference and the matcher is called to find a solution.

We then check the solution to make sure custom_loads were not violated.

To run this test you must be running OR with a clean db. See README for details.

'''

from collections import defaultdict
import numpy as np

from matcher.fields import Configuration
from matcher.Match import Match
from helpers.Params import Params

H = 10.0
M = 3.0

def test_custom_load_zero(test_util):
    '''
    Reviewer 0 has a custom load of 0, and high scores across the board.

    Reviewer 0 should not be assigned any papers.
    '''

    score_matrix = np.array([
        [H, H, H],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0]
    ])

    num_papers = 3
    num_reviewers = 4
    num_reviews_per_paper = 2
    reviewer_max_papers = 2

    params = Params({
        Params.NUM_PAPERS: num_papers,
        Params.NUM_REVIEWERS: num_reviewers,
        Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
        Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
        Params.CUSTOM_LOAD_CONFIG: {
            Params.CUSTOM_LOAD_MAP: {
                0: 0
            }
        },
        Params.SCORES_CONFIG: {
            Params.SCORES_SPEC: {
                'affinity': {
                    'weight': 1,
                    'default': 0
                }
            },
            Params.SCORE_TYPE: Params.MATRIX_SCORE,
            Params.SCORE_MATRIX: score_matrix
        }
    })

    test_util.set_test_params(params)
    test_util.build_conference()
    match = Match(test_util.client, test_util.get_conference().get_config_note())
    match.compute_match()

    conference = test_util.get_conference()
    assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE

    total_reviews = num_reviews_per_paper * len(conference.get_paper_notes())
    assignment_edges = conference.get_assignment_edges()
    assert len(assignment_edges) == total_reviews

    reviewers = conference.reviewers
    assignments_by_reviewer = defaultdict(list)
    for edge in assignment_edges:
        assignments_by_reviewer[edge.tail].append(edge.head)

    assert not assignments_by_reviewer[reviewers[0]]

def test_custom_load_one(test_util):
    '''
    Reviewers 0 and 1 should have at most 1 assignment each.
    '''
    score_matrix = np.array([
        [H, H, H],
        [H, H, H],
        [0, 0, 0],
        [0, 0, 0]
    ])

    num_papers = 3
    num_reviewers = 4
    num_reviews_per_paper = 2
    reviewer_max_papers = 2

    params = Params({
        Params.NUM_PAPERS: num_papers,
        Params.NUM_REVIEWERS: num_reviewers,
        Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
        Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
        Params.CUSTOM_LOAD_CONFIG: {
            Params.CUSTOM_LOAD_MAP: {
                0: 1,
                1: 1
            }
        },
        Params.SCORES_CONFIG: {
            Params.SCORE_TYPE: Params.MATRIX_SCORE,
            Params.SCORE_MATRIX: score_matrix,
            Params.SCORES_SPEC: {
                'affinity': {
                    'weight': 1,
                    'default': 0
                }
            }
        }
    })

    test_util.set_test_params(params)
    test_util.build_conference()
    match = Match(test_util.client, test_util.get_conference().get_config_note())
    match.compute_match()
    conference = test_util.get_conference()

    assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE

    total_reviews = num_reviews_per_paper * len(conference.get_paper_notes())
    assignment_edges = conference.get_assignment_edges()
    assert len(assignment_edges) == total_reviews

    reviewers = conference.reviewers

    assignments_by_reviewer = defaultdict(list)
    for edge in assignment_edges:
        assignments_by_reviewer[edge.tail].append(edge.head)

    # ensure that reviewers 0 and 1 have at most 1 assignment
    assert len(assignments_by_reviewer[reviewers[0]]) <= 1
    assert len(assignments_by_reviewer[reviewers[1]]) <= 1
    assert len(assignments_by_reviewer[reviewers[2]]) <= 2
    assert len(assignments_by_reviewer[reviewers[3]]) <= 2

def test_custom_overload(test_util):
    '''
    Default maximum number of assignments per reviewer is 1,
    but reviewer 3 has a custom load of 3.

    All assignments should be given to reviewer 3, and none should be given to the others.
    '''
    score_matrix = np.array([
        [H, H, H],
        [H, H, H],
        [H, H, H],
        [0, 0, 0]
    ])

    num_papers = 3
    num_reviews_per_paper = 1
    num_reviewers = 4
    reviewer_max_papers = 1

    params = Params({
        Params.NUM_PAPERS: num_papers,
        Params.NUM_REVIEWERS: num_reviewers,
        Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
        Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
        Params.CUSTOM_LOAD_CONFIG: {
            Params.CUSTOM_LOAD_MAP: {
                0: 0,
                1: 0,
                2: 0,
                3: 3
            }
        },
        Params.SCORES_CONFIG: {
            Params.SCORE_MATRIX: score_matrix,
            Params.SCORE_TYPE: Params.MATRIX_SCORE,
            Params.SCORES_SPEC: {
                'affinity': {'weight': 1, 'default': 0}
            }
        }
    })

    test_util.set_test_params(params)
    test_util.build_conference()
    match = Match(test_util.client, test_util.get_conference().get_config_note())
    match.compute_match()
    conference = test_util.get_conference()

    assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE

    reviewers = conference.reviewers

    assignment_edges = conference.get_assignment_edges()
    assignments_by_reviewer = defaultdict(list)
    for edge in assignment_edges:
        assignments_by_reviewer[edge.tail].append(edge.head)

    assert not assignments_by_reviewer[reviewers[0]]
    assert not assignments_by_reviewer[reviewers[1]]
    assert not assignments_by_reviewer[reviewers[2]]
    assert len(assignments_by_reviewer[reviewers[3]]) == 3
