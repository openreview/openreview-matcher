import time
import json
import traceback

from matcher.fields import Configuration
from helpers.ConferenceConfig import ConferenceConfig
import openreview
import matcher

class TestUtil:
    instance = None

    @classmethod
    def get_instance(cls, base_url, flask_test_client, silent=True, use_edge_builder=True):
        if not cls.instance:
            cls.instance = TestUtil(
                base_url, flask_test_client, silent=silent, use_edge_builder=use_edge_builder)
        return cls.instance

    def __init__(self, base_url, flask_test_client, silent=True, use_edge_builder=True):
        self._test_count = 0
        self.or_client_user = 'openreview.net'
        self.or_client_password = '1234'
        self.client = self.get_client(base_url)
        self.create_super_user()
        self.flask_test_client = flask_test_client
        self.silent = silent
        self.initialize_matcher_app()
        self.conf_builder = 'Edge' if use_edge_builder else 'Old'


    def use_edge_conf_builder(self):
        return self.conf_builder == 'Edge'

    def set_silent(self, silent):
        self.silent = silent

    def initialize_matcher_app(self):
        '''
        The matcher app config needs to know to use real (not mock)
        openreview-py API and it needs the superuser credentials.
        '''
        matcher.app.config['TESTING'] = True
        matcher.app.config['USE_API'] = True
        matcher.app.config['OPENREVIEW_USERNAME'] = self.or_client_user
        matcher.app.config['OPENREVIEW_PASSWORD'] = self.or_client_password

        # No need for web app logging during test
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True

    def enable_logging(self):
        matcher.app.logger.disabled = False
        matcher.app.logger.parent.disabled = False

    def get_client(self, base_url):
        return openreview.Client(baseurl=base_url)

    def create_super_user(self):
        assert self.client

        register_result = self.client.register_user(
            email=self.or_client_user,
            first='Super',
            last='User',
            password=self.or_client_password)

        activation_result = self.client.activate_user(
            'openreview.net',
            {
                'names': [
                    {
                        'first': 'Super',
                        'last': 'User',
                        'username': '~Super_User1'
                    }
                ],
                'emails': ['openreview.net'],
                'preferredEmail': 'info@openreview.net'
            }
        )
        assert activation_result

        group = self.client.get_group('openreview.net')
        assert group and group.members == ['~Super_User1']


    def get_conference(self):
        return self.conf

    def check_match_error(self, reason):
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_ERROR
        print("Reason expecting error:", reason)

    def set_test_params(self, params):
        self.params = params
        if not self.silent:
            self.params.print_params()

    def next_conference_count(self):
        self._test_count += 1
        return self._test_count

    def test_matcher(self):
        self.build_conference()
        self.run_matcher()

    def build_conference(self):
        self.next_conference_count()
        self.conf = ConferenceConfig(self.client, self._test_count, self.params)

    def run_matcher(self):
        config_id = self.conf.config_note_id
        url = '/match'
        body = {'configNoteId': self.conf.config_note_id}
        headers = {'Authorization': 'Bearer Valid'}
        response = self.post_json(url, body, headers=headers)

        assert response.status_code == 200
        # The matcher does its real work in a separate thread,
        # which will write a status into the configuration note when it's complete
        # (successful or error)
        # so we want to wait until the status changes to one of those things.
        done = self.wait_until_complete(config_id)

    def wait_until_complete(self, config_id):
        iterations = 120
        iteration_duration = 1
        status = self.conf.get_config_note_status()

        for t in range(iterations):
            if status == Configuration.STATUS_COMPLETE:
                return True

            time.sleep(iteration_duration)
            status = self.conf.get_config_note_status()

        raise TimeoutError('Match did not complete within {} iterations'.format(max_checks))

    def post_json(self, url, json_dict, headers=None):
        config_note = json.dumps(json_dict)
        if headers:
            return self.flask_test_client.post(
                url,
                data=config_note,
                content_type='application/json',
                headers=headers)

        return self.flask_test_client.post(
            url,
            data=config_note,
            content_type='application/json')
