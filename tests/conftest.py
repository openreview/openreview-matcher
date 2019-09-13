'''
Defines pytest fixtures that maintain a persistent state
(in relation to the test openreview server) between tests.
'''

import os
import datetime
import time
import random
import subprocess
import requests
import pytest

import openreview

import matcher.service

AFFINITY_SCORE_FILE = './affinity_scores'

def ping_url(url):
    iterations = 300
    iteration_duration = 0.1

    for t in range(iterations):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError as e:
            time.sleep(iteration_duration)

    raise TimeoutError('no response within {} iterations'.format(iterations))

def wait_for_status(client, config_note_id):
    '''
    Repeatedly requests the configuration note until its status is not 'Initialized' or 'Running',
    then returns the status.
    '''
    max_iterations = 100
    interval_duration = 0.5
    for iteration in range(max_iterations):
        config_note = client.get_note(config_note_id)
        if config_note.content['status'] in ['Initialized', 'Running']:
            time.sleep(interval_duration)
        else:
            return config_note.content['status']

    raise TimeoutError('matcher did not finish')

def initialize_superuser(config):
    '''register and activate the superuser account'''

    # need to create a guest client before we can login with the supser user
    guest_client = openreview.Client(
        username='',
        password='',
        baseurl=config['OPENREVIEW_BASEURL']

    )

    register_result = guest_client.register_user(
        email=config['OPENREVIEW_USERNAME'],
        first=config['SUPERUSER_FIRSTNAME'],
        last=config['SUPERUSER_LASTNAME'],
        password=config['OPENREVIEW_PASSWORD']
    )

    activation_result = guest_client.activate_user(
        config['OPENREVIEW_USERNAME'],
        {
            'names': [{
                'first': config['SUPERUSER_FIRSTNAME'],
                'last': config['SUPERUSER_LASTNAME'],
                'username': config['SUPERUSER_TILDE_ID']
            }],
            'emails': [config['OPENREVIEW_USERNAME']],
            'preferredEmail': config['SUPERUSER_EMAIL']
        }
    )

    superuser_client = openreview.Client(
        username=config['OPENREVIEW_USERNAME'],
        password=config['OPENREVIEW_PASSWORD'],
        baseurl=config['OPENREVIEW_BASEURL']
    )

    return superuser_client

def clean_start_conference(client, conference_id, num_reviewers, num_papers, reviews_per_paper):
    builder = openreview.conference.ConferenceBuilder(client)
    builder.set_conference_id(conference_id)
    builder.set_submission_stage(
        due_date=datetime.datetime(2019, 3, 25, 23, 59),
        remove_fields=['authors', 'abstract', 'pdf', 'keywords', 'TL;DR'])

    conference = builder.get_result()

    submission_invitation = client.get_invitation(conference.get_submission_id())
    submission_invitation.reply['content']['authorids'] = {
        'values-regex': '.*'
    }
    submission_invitation = client.post_invitation(submission_invitation)

    reviewers = []

    # TODO: is there a better way to handle affinity scores?
    # Maybe conference.setup_matching() should allow a score matrix as input
    with open(AFFINITY_SCORE_FILE, 'w') as file_handle:
        for paper_number in range(num_papers):
            content = {
                'title': 'Test_Paper_{}'.format(paper_number),
                'authorids': [
                    'testauthor{}{}@test.com'.format(paper_number, author_code) \
                    for author_code in ['A', 'B', 'C']
                ]
            }
            submission = openreview.Note(**{
                'signatures': ['~Super_User1'],
                'writers': [conference.id],
                'readers': [conference.id],
                'content': content,
                'invitation': conference.get_submission_id()
            })
            posted_submission = client.post_note(submission)

            for reviewer_number in range(num_reviewers):
                reviewer = '~Test_Reviewer{}'.format(reviewer_number)
                reviewers.append(reviewer)
                score = random.random()
                row = [posted_submission.forum, reviewer, '{:.3f}'.format(score)]
                file_handle.write(','.join(row) + '\n')

    conference.set_authors()
    conference.set_reviewers(emails=reviewers)

    conference.setup_matching(
        affinity_score_file=AFFINITY_SCORE_FILE
    )

    return conference

@pytest.fixture
def openreview_context(scope='function'):
    '''
    A pytest fixture for setting up a clean OpenReview test instance:

    1.  Opens a subprocess running `scripts/clean_start_app.js` from the OpenReview home directory.
    2.  When the OpenReview instance responds to pings, creates a super user account for testing.
    3.  Yields the process, Flask app, and openreview.Client object to the test function.

    `scope` argument is set to 'function', so each function will get a clean test instance.
    '''


    app = matcher.service.create_app(config={
            'LOG_FILE': 'pytest.log',
            'OPENREVIEW_USERNAME': 'openreview.net',
            'OPENREVIEW_PASSWORD': '1234',
            'OPENREVIEW_BASEURL': 'http://localhost:3000',
            'SUPERUSER_FIRSTNAME': 'Super',
            'SUPERUSER_LASTNAME': 'User',
            'SUPERUSER_TILDE_ID': '~Super_User1',
            'SUPERUSER_EMAIL': 'info@openreview.net',
        })

    openreview_home = os.getenv('OPENREVIEW_HOME')
    os.chdir(openreview_home)

    try:
        # this calls the clean_start_app.js script, and silences its output
        # (this makes reading test errors easier)

        os.environ['NODE_ENV'] = 'circleci'
        openreview_process = subprocess.Popen(
            ['node', os.path.join(openreview_home, 'scripts', 'clean_start_app.js')],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )

        process_ready = ping_url(app.config['OPENREVIEW_BASEURL'])

        superuser_client = initialize_superuser(app.config)

        with app.app_context():
            yield {
                'app': app,
                'test_client': app.test_client(),
                'openreview_client': superuser_client
            }

    finally:
        openreview_process.kill()

if __name__ == '__main__':

    config = {
        'OPENREVIEW_USERNAME': 'openreview.net',
        'OPENREVIEW_PASSWORD': '1234',
        'OPENREVIEW_BASEURL': 'http://localhost:3000',
        'SUPERUSER_FIRSTNAME': 'Super',
        'SUPERUSER_LASTNAME': 'User',
        'SUPERUSER_TILDE_ID': '~Super_User1',
        'SUPERUSER_EMAIL': 'info@openreview.net'
    }

    superuser_client = initialize_superuser(config)

    # TODO: Parameterize this
    num_reviewers, num_papers, reviews_per_paper = 50, 50, 1

    conference_id = 'ICLR.cc/2019/Conference'
    conference = clean_start_conference(
        superuser_client, conference_id, num_reviewers, num_papers, reviews_per_paper)

