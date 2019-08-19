'''
End-to-end integration tests with OpenReview server.
'''

import json
import time
import requests
import openreview

from matcher.matcher_client import MatcherClient

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

    # I'm instantiating a MatcherClient here because it has the `get_all_edges` function,
    # which openreview.Client does not have.
    # TODO: Move get_all_edges functionality to openreview.Client.
    matcher_client = MatcherClient(
        username=app.config['OPENREVIEW_USERNAME'],
        password=app.config['OPENREVIEW_PASSWORD'],
        baseurl=app.config['OPENREVIEW_BASEURL'],
        config_id=config_note.id
    )
    paper_assignment_edges = matcher_client.get_all_edges(
        conference.get_paper_assignment_id(conference.get_reviewers_id())
    )

    assert len(paper_assignment_edges) == num_papers * reviews_per_paper

