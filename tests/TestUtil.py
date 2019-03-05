import functools
import time
import json
import pprint
from fields import Configuration
from conference_config import Params, ConferenceConfig
from AssignmentChecker import AssignmentChecker
import openreview
import matcher


def time_ms ():
    return int(round(time.time() * 1000))

class TestUtil:
    instance = None

    @classmethod
    def get_instance (cls, base_url):
        if not cls.instance:
            cls.instance = TestUtil(base_url)
        return cls.instance

    def __init__(self, base_url):
        self.test_count = 0
        self.get_client(base_url)

    def get_client(self, base_url):
        self.client = openreview.Client(baseurl = base_url)
        assert self.client is not None, "Client is none"
        username = 'openreview.net'
        password = '1234'
        res = self.client.register_user(email = username, first = 'Super', last = 'User', password = password)
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

        # The matcher app config needs to know to use real openreview-py API and it needs the superuser
        # credentials created above
        matcher.app.config['TESTING'] = True
        matcher.app.config['USE_API'] = True
        matcher.app.config['OPENREVIEW_USERNAME'] = username
        matcher.app.config['OPENREVIEW_PASSWORD'] = password


    def get_review_supply (self, custom_loads):
        return functools.reduce(lambda x, value:x + value, custom_loads.values(), 0)

    def check_completed_match(self, check_loads=True, check_constraints=True):
        config_stat = TestUtil.get_config_status(self.client, self.conf)
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_COMPLETE)
        assignment_notes = self.conf.get_assignment_notes()
        assert len(assignment_notes) == self.params[Params.NUM_PAPERS], "Number of assignments {} is not same as number of papers {}".format(len(assignment_notes), self.params[Params.NUM_PAPERS])
        self.show_custom_loads()
        print()
        self.show_constraints()
        AssignmentChecker(self.conf, check_loads, check_constraints, assignment_notes).check_results()

    def check_failed_match(self):
        config_stat = TestUtil.get_config_status(self.client, self.conf)
        custom_loads = self.conf.get_custom_loads()
        actual_supply = self.get_review_supply(custom_loads)
        assert config_stat == Configuration.STATUS_ERROR, "Failure: Config status is {} expected {}".format(config_stat,
                                                                                                            Configuration.STATUS_ERROR)
        print("Got the expected error because actual supply {} < demand {}".format(actual_supply, self.params[Params.DEMAND]))

    def set_and_print_test_params (self, params):
        self.params = params
        supply_deduction_from_custom_loads = 0
        if self.params.get(Params.CUSTOM_LOAD_SUPPLY_DEDUCTION):
            supply_deduction_from_custom_loads = self.params[Params.CUSTOM_LOAD_CONFIG][Params.CUSTOM_LOAD_SUPPLY_DEDUCTION]

        self.params[Params.DEMAND] = self.params[Params.NUM_PAPERS] * self.params[Params.NUM_REVIEWS_NEEDED_PER_PAPER]
        self.params[Params.THEORETICAL_SUPPLY] = self.params[Params.NUM_REVIEWERS] * self.params[Params.REVIEWER_MAX_PAPERS]
        self.params[Params.ACTUAL_SUPPLY] = self.params[Params.THEORETICAL_SUPPLY] - supply_deduction_from_custom_loads

        print("\n\nTesting with {} papers, {} reviewers. \nEach paper needs at least {} review(s).  \nReviewer reviews max of {} paper(s). \nSupply: {} Demand: {}.\nActual Supply:{}\n\tcustom_load deduction {}\nLock Constraints: {}\nVeto Constraints: {}".
              format(self.params[Params.NUM_PAPERS], self.params[Params.NUM_REVIEWERS], self.params[Params.NUM_REVIEWS_NEEDED_PER_PAPER],
                     self.params[Params.REVIEWER_MAX_PAPERS], self.params[Params.THEORETICAL_SUPPLY], self.params[Params.DEMAND],
                     self.params[Params.ACTUAL_SUPPLY], supply_deduction_from_custom_loads,
                     self.params.get(Params.CONSTRAINTS_CONFIG,{}).get(Params.CONSTRAINTS_LOCKS),
                     self.params.get(Params.CONSTRAINTS_CONFIG,{}).get(Params.CONSTRAINTS_VETOS)
                     ))

    def show_custom_loads (self):
        print("Custom_loads in config {} are:".format(self.conf.config_note_id))
        pprint.pprint(self.conf.get_custom_loads())

    def show_constraints (self):
        print("Constraints in config {} are:".format(self.conf.config_note_id))
        pprint.pprint(self.conf.get_constraints())

    # method name needs _ so that unittest won't run this as a test
    def test_matcher(self, flask_app, params):
        self.test_count += 1
        print("Running test", self.test_count)
        self.conf = ConferenceConfig(self.client, self.test_count, params)
        config_id = self.conf.config_note_id
        print("Testing Config " + config_id)

        # Disable logging in the web app the test cases do the necessary result-checking when they expect
        # errors to happen inside the matcher.
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True
        response = self.post_json(flask_app, '/match', {'configNoteId': self.conf.config_note_id },
                             headers={'Authorization': 'Bearer Valid'})
        print(time_ms(),"Waiting for matcher to finish solving...")
        self.wait_until_complete(config_id)
        # self.sleep_for_seconds(config_id, 5)
        assert response.status_code == 200

    def wait_until_complete(self, config_id):
        stat = TestUtil.get_config_status(self.client,self.conf)
        while stat in [Configuration.STATUS_INITIALIZED, Configuration.STATUS_RUNNING]:
            time.sleep(0.5)
            stat = TestUtil.get_config_status(self.client,self.conf)
        print("After waiting configuration status is:", stat, "Done!\n")

    def post_json(self, flask_app, url, json_dict, headers=None):
        """Send dictionary json_dict as a json to the specified url """
        config_note = json.dumps(json_dict)
        if headers:
            return flask_app.post(url, data=config_note, content_type='application/json', headers=headers)
        else:
            return flask_app.post(url, data=config_note, content_type='application/json')

    @classmethod
    def get_config_status (cls, client, conf):
        config_note = client.get_note(conf.config_note_id)
        return config_note.content['status']