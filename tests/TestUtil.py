import time
import json
import pprint
from matcher.fields import Configuration
from conference_config import ConferenceConfig
from AssignmentChecker import AssignmentChecker
import openreview
import matcher


def time_ms ():
    return int(round(time.time() * 1000))

class TestUtil:
    instance = None

    @classmethod
    def get_instance (cls, base_url, flask_test_client):
        if not cls.instance:
            cls.instance = TestUtil(base_url, flask_test_client)
        return cls.instance

    def __init__(self, base_url, flask_test_client):
        self.test_count = 0
        self.OR_CLIENT_USER = 'openreview.net'
        self.OR_CLIENT_PASSWORD = '1234'
        self.get_client(base_url)
        self.flask_test_client = flask_test_client
        self.initialize_matcher_app()

    def initialize_matcher_app (self):
        # The matcher app config needs to know to use real (not mock) openreview-py API and it needs the superuser
        # credentials.
        matcher.app.config['TESTING'] = True
        matcher.app.config['USE_API'] = True
        matcher.app.config['OPENREVIEW_USERNAME'] = self.OR_CLIENT_USER
        matcher.app.config['OPENREVIEW_PASSWORD'] = self.OR_CLIENT_PASSWORD
        # Disable logging in the web app because it sends stuff to stdout that we don't want to see while testing
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True

    def get_client(self, base_url):
        self.client = openreview.Client(baseurl = base_url)
        assert self.client is not None, "Client is none"
        res = self.client.register_user(email = self.OR_CLIENT_USER, first = 'Super', last = 'User', password = self.OR_CLIENT_PASSWORD)
        assert res, "Res i none"
        res = self.client.activate_user('openreview.net', {
            'names': [
                {
                    'first': 'Super',
                    'last': 'User',
                    'username': '~Super_User1'
                }
            ],
            'emails': ['openreview.net'],
            'preferredEmail': 'info@openreview.net'
        })
        assert res, "Res i none"
        group = self.client.get_group(id = 'openreview.net')
        assert group
        assert group.members == ['~Super_User1']

    def check_completed_match(self, check_loads=True, check_constraints=True, check_conflicts=True):
        self.show_custom_loads()
        print()
        self.show_constraints()
        print()
        self.show_conflicts()
        AssignmentChecker(self.conf, check_loads, check_constraints, check_conflicts, self.conf.get_assignment_notes()).check_results()

    def check_match_error(self, reason):
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_ERROR, "Error: Config status is {} expected {}".format(config_stat, Configuration.STATUS_ERROR)
        print("Reason expecting error:", reason)

    def set_and_print_test_params (self, params):
        self.params = params
        self.params.print_params()

    def show_custom_loads (self):
        print("Custom_loads in config {} are:".format(self.conf.config_note_id))
        pprint.pprint(self.conf.get_custom_loads())

    def show_constraints (self):
        print("Constraints in config {} are:".format(self.conf.config_note_id))
        pprint.pprint(self.conf.get_constraints())

    def show_conflicts (self):
        print("Conflicts in metadata objects are: TODO ")
        #TODO Create a dict with keys that are forum_ids and values that are lists of users that conflict with the paper
        pass


    def test_matcher (self):
        self.test_count += 1
        self.build_conference()
        self.run_matcher()

    def build_conference (self):
        self.conf = ConferenceConfig(self.client, self.test_count, self.params)

    def run_matcher (self):
        config_id = self.conf.config_note_id
        response = self.post_json('/match', {'configNoteId': self.conf.config_note_id },
                                  headers={'Authorization': 'Bearer Valid'})
        assert response.status_code == 200
        # The matcher does its real work in a separate thread which will write a status into the configuration note when its complete (successful or error)
        # so we want to wait until the status changes to one of those things.
        self.wait_until_complete(config_id)

    def wait_until_complete(self, config_id):
        stat = self.conf.get_config_note_status()
        while stat in [Configuration.STATUS_INITIALIZED, Configuration.STATUS_RUNNING]:
            time.sleep(0.5)
            stat = self.conf.get_config_note_status()
        print("After waiting configuration status is:", stat, "Done!\n")

    def post_json(self, url, json_dict, headers=None):
        """Send dictionary json_dict as a json to the specified url """
        config_note = json.dumps(json_dict)
        if headers:
            return self.flask_test_client.post(url, data=config_note, content_type='application/json', headers=headers)
        else:
            return self.flask_test_client.post(url, data=config_note, content_type='application/json')
