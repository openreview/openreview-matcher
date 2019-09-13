'''
End-to-end integration tests with OpenReview server.
'''

import json
import time
import requests
import pytest
import openreview

from matcher.service.openreview_interface import get_all_edges

from conftest import clean_start_conference, wait_for_status

def test_integration_basic(openreview_context):
    '''
    Basic integration test. Makes use of the OpenReview Builder
    '''
    openreview_client = openreview_context['openreview_client']
    test_client = openreview_context['test_client']
    app = openreview_context['app']

    conference_id = 'ICLR.cc/2019/Conference'
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        'title': 'integration-test',
        'max_users': str(reviews_per_paper),
        'min_users': str(reviews_per_paper),
        'max_papers': str(max_papers),
        'min_papers': str(min_papers),
        'alternates': str(alternates),
        'config_invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'paper_invitation': conference.get_blind_submission_id(),
        'assignment_invitation': conference.get_paper_assignment_id(reviewers_id),
        'aggregate_score_invitation': '{}/-/Aggregate_Score'.format(reviewers_id),
        'conflicts_invitation': conference.get_conflict_score_id(reviewers_id),
        'custom_load_invitation': '{}/-/Custom_Load'.format(reviewers_id),
        'match_group': reviewers_id,
        'scores_specification': {
            conference.get_affinity_score_id(reviewers_id): {
                'weight': 1.0,
                'default': 0.0
            }
        },
        'status': 'Initialized'
    }

    config_note = openreview.Note(**{
        'invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'readers': [conference.get_id()],
        'writers': [conference.get_id()],
        'signatures': [conference.get_id()],
        'content': config
    })

    config_note = openreview_client.post_note(config_note)
    assert config_note

    response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json',
        headers=openreview_client.headers
    )
    assert response.status_code == 200

    matcher_status = wait_for_status(openreview_client, config_note.id)
    assert matcher_status == 'Complete'

    openreview_client.get_edges()

    paper_assignment_edges = get_all_edges(
        openreview_client,
        conference.get_paper_assignment_id(conference.get_reviewers_id())
    )

    assert len(paper_assignment_edges) == num_papers * reviews_per_paper

def test_routes_missing_header(openreview_context):
    '''request with missing header should response with 400'''
    openreview_client = openreview_context['openreview_client']
    test_client = openreview_context['test_client']
    app = openreview_context['app']

    conference_id = 'ICLR.cc/2019/Conference'
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        'title': 'integration-test',
        'max_users': str(reviews_per_paper),
        'min_users': str(reviews_per_paper),
        'max_papers': str(max_papers),
        'min_papers': str(min_papers),
        'alternates': str(alternates),
        'config_invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'paper_invitation': conference.get_blind_submission_id(),
        'assignment_invitation': conference.get_paper_assignment_id(reviewers_id),
        'aggregate_score_invitation': '{}/-/Aggregate_Score'.format(reviewers_id),
        'conflicts_invitation': conference.get_conflict_score_id(reviewers_id),
        'custom_load_invitation': '{}/-/Custom_Load'.format(reviewers_id),
        'match_group': reviewers_id,
        'scores_specification': {
            conference.get_affinity_score_id(reviewers_id): {
                'weight': 1.0,
                'default': 0.0
            }
        },
        'status': 'Initialized'
    }

    config_note = openreview.Note(**{
        'invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'readers': [conference.get_id()],
        'writers': [conference.get_id()],
        'signatures': [conference.get_id()],
        'content': config
    })

    config_note = openreview_client.post_note(config_note)
    assert config_note

    missing_header_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json'
    )
    assert missing_header_response.status_code == 400

def test_routes_missing_config(openreview_context):
    '''should return 404 if config note doesn't exist'''

    openreview_client = openreview_context['openreview_client']
    test_client = openreview_context['test_client']
    app = openreview_context['app']

    missing_config_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': 'BAD_CONFIG_NOTE_ID'}),
        content_type='application/json',
        headers=openreview_client.headers
    )
    assert missing_config_response.status_code == 404

@pytest.mark.skip # TODO: fix the authorization so that this test passes.
def test_routes_bad_token(openreview_context):
    '''should return 400 if token is bad'''
    openreview_client = openreview_context['openreview_client']
    test_client = openreview_context['test_client']
    app = openreview_context['app']

    bad_token_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json',
        headers={'Authorization': 'BAD_TOKEN'}
    )
    assert bad_token_response.status_code == 400

@pytest.mark.skip # TODO: fix authorization so that this test passes.
def test_routes_forbidden_config(openreview_context):
    '''should return 403 if user does not have permission on config note'''

    openreview_client = openreview_context['openreview_client']
    test_client = openreview_context['test_client']
    app = openreview_context['app']

    conference_id = 'ICLR.cc/2019/Conference'
    num_reviewers = 1
    num_papers = 1
    reviews_per_paper = 1
    max_papers = 1
    min_papers = 0
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        'title': 'integration-test',
        'max_users': str(reviews_per_paper),
        'min_users': str(reviews_per_paper),
        'max_papers': str(max_papers),
        'min_papers': str(min_papers),
        'alternates': str(alternates),
        'config_invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'paper_invitation': conference.get_blind_submission_id(),
        'assignment_invitation': conference.get_paper_assignment_id(reviewers_id),
        'aggregate_score_invitation': '{}/-/Aggregate_Score'.format(reviewers_id),
        'conflicts_invitation': conference.get_conflict_score_id(reviewers_id),
        'custom_load_invitation': '{}/-/Custom_Load'.format(reviewers_id),
        'match_group': reviewers_id,
        'scores_specification': {
            conference.get_affinity_score_id(reviewers_id): {
                'weight': 1.0,
                'default': 0.0
            }
        },
        'status': 'Initialized'
    }

    config_note = openreview.Note(**{
        'invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'readers': [conference.get_id()],
        'writers': [conference.get_id()],
        'signatures': [conference.get_id()],
        'content': config
    })

    config_note = openreview_client.post_note(config_note)
    assert config_note

    guest_client = openreview.Client(
        username='',
        password='',
        baseurl=app.config['OPENREVIEW_BASEURL']
    )

    forbidden_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json',
        headers=guest_client.headers
    )
    assert forbidden_response.status_code == 403

def test_routes_already_running(openreview_context):
    '''should return 400 if the match is already running'''

    openreview_client = openreview_context['openreview_client']
    test_client = openreview_context['test_client']
    app = openreview_context['app']

    conference_id = 'ICLR.cc/2019/Conference'
    num_reviewers = 1
    num_papers = 1
    reviews_per_paper = 1
    max_papers = 1
    min_papers = 0
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        'title': 'integration-test',
        'max_users': str(reviews_per_paper),
        'min_users': str(reviews_per_paper),
        'max_papers': str(max_papers),
        'min_papers': str(min_papers),
        'alternates': str(alternates),
        'config_invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'paper_invitation': conference.get_blind_submission_id(),
        'assignment_invitation': conference.get_paper_assignment_id(reviewers_id),
        'aggregate_score_invitation': '{}/-/Aggregate_Score'.format(reviewers_id),
        'conflicts_invitation': conference.get_conflict_score_id(reviewers_id),
        'custom_load_invitation': '{}/-/Custom_Load'.format(reviewers_id),
        'match_group': reviewers_id,
        'scores_specification': {
            conference.get_affinity_score_id(reviewers_id): {
                'weight': 1.0,
                'default': 0.0
            }
        },
        'status': 'Running'
    }

    config_note = openreview.Note(**{
        'invitation': '{}/-/Assignment_Configuration'.format(reviewers_id),
        'readers': [conference.get_id()],
        'writers': [conference.get_id()],
        'signatures': [conference.get_id()],
        'content': config
    })

    config_note = openreview_client.post_note(config_note)
    assert config_note

    already_running_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json',
        headers=openreview_client.headers
    )
    assert already_running_response.status_code == 400
