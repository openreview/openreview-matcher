'''
A test suite for testing `matcher/routes.py`

Verifies that status codes are responding to requests as intended.
'''

import json
import pytest
import openreview
from matcher.matcher_client import MatcherClient

from conftest import clean_start_conference, wait_for_status

# pylint:disable=unused-argument
@pytest.fixture
def routes_context(openreview_context, scope='module'):
    '''setup context for routes tests'''
    app = openreview_context['app']
    test_client = openreview_context['test_client']
    openreview_client = openreview_context['openreview_client']

    conference = clean_start_conference(
        openreview_client,
        'ICLR.cc/2019/Conference', # conference_id
        3, # num_reviewers
        3, # num_papers
        1, # reviews_per_paper
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        'title': 'routes-test',
        'max_users': '1', # reviews_per_paper
        'min_users': '1', # reviews_per_paper
        'max_papers': '1',
        'min_papers': '1',
        'alternates': '0',
        'config_invitation': '{}/-/Reviewing/Assignment_Configuration'.format(reviewers_id),
        'paper_invitation': conference.get_blind_submission_id(),
        'assignment_invitation': conference.get_paper_assignment_id(reviewers_id),
        'aggregate_score_invitation': '{}/-/Reviewing/Aggregate_Score'.format(reviewers_id),
        'conflicts_invitation': conference.get_conflict_score_id(reviewers_id),
        'custom_load_invitation': '{}/-/Reviewing/Custom_Load'.format(reviewers_id),
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
        'invitation': '{}/-/Reviewing/Assignment_Configuration'.format(reviewers_id),
        'readers': [conference.get_id()],
        'writers': [conference.get_id()],
        'signatures': [conference.get_id()],
        'content': config
    })

    config_note = openreview_client.post_note(config_note)
    assert config_note

    matcher_client = MatcherClient(
        username=app.config['OPENREVIEW_USERNAME'],
        password=app.config['OPENREVIEW_PASSWORD'],
        baseurl=app.config['OPENREVIEW_BASEURL'],
        config_id=config_note.id
    )

    yield {
        'app': app,
        'openreview_client': openreview_client,
        'test_client': test_client,
        'matcher_client': matcher_client,
        'config_note': config_note
    }

# pylint:disable=redefined-outer-name
def test_routes_missing_header(routes_context):
    '''request with missing header should response with 400'''
    test_client = routes_context['test_client']
    config_note = routes_context['config_note']
    missing_header_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json'
    )
    assert missing_header_response.status_code == 400

def test_routes_missing_config(routes_context):
    '''should return 404 if config note doesn't exist'''
    test_client = routes_context['test_client']
    openreview_client = routes_context['openreview_client']
    missing_config_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': 'BAD_CONFIG_NOTE_ID'}),
        content_type='application/json',
        headers=openreview_client.headers
    )
    assert missing_config_response.status_code == 404

@pytest.mark.skip # TODO: fix the authorization so that this test passes.
def test_routes_bad_token(routes_context):
    '''should return 400 if token is bad'''
    test_client = routes_context['test_client']
    config_note = routes_context['config_note']
    bad_token_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json',
        headers={'Authorization': 'BAD_TOKEN'}
    )
    assert bad_token_response.status_code == 400

@pytest.mark.skip # TODO: fix authorization so that this test passes.
def test_routes_forbidden_config(routes_context):
    '''should return 403 if user does not have permission on config note'''
    app = routes_context['app']
    test_client = routes_context['test_client']
    config_note = routes_context['config_note']

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

def test_routes_already_running(routes_context):
    '''should return 400 if the match is already running'''
    test_client = routes_context['test_client']
    config_note = routes_context['config_note']
    openreview_client = routes_context['openreview_client']
    matcher_client = routes_context['matcher_client']

    matcher_client.set_status('Running')

    assert matcher_client.config_note.content['status'] == 'Running'

    already_running_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json',
        headers=openreview_client.headers
    )
    assert already_running_response.status_code == 400

def test_routes_success(routes_context):
    '''should return 200 if the match is successful'''
    test_client = routes_context['test_client']
    config_note = routes_context['config_note']
    openreview_client = routes_context['openreview_client']
    matcher_client = routes_context['matcher_client']

    matcher_client.set_status('Initialized')
    successful_response = test_client.post(
        '/match',
        data=json.dumps({'configNoteId': config_note.id}),
        content_type='application/json',
        headers=openreview_client.headers
    )
    assert successful_response.status_code == 200

    matcher_status = wait_for_status(openreview_client, config_note.id)

    assert matcher_status == 'Complete'
