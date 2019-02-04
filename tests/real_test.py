import unittest
import json
import matcher
import os
import openreview
from test_conf import TestConf
from matcher.fields import Configuration


def post_json(client, url, json_dict, headers=None):
    """Send dictionary json_dict as a json to the specified url """
    config_note = json.dumps(json_dict)
    if headers:
        return client.post(url, data=config_note, content_type='application/json', headers=headers)
    else:
        return client.post(url, data=config_note, content_type='application/json')

def json_of_response(response):
    """Decode json from response"""
    return json.loads(response.data.decode('utf8'))


# N.B.  The app we are testing uses a logger that generates error messages when given bad inputs.  This test fixture does just that.
# It verifies that bad inputs result in correct error status returns.  However you will see stack dumps which are also produced by the logger
# These stack dumps do not represent test cases that are failing!
class TestRealDataset(unittest.TestCase):

    # called once at beginning of suite
    @classmethod
    def setUpClass(cls):
        or_baseurl = os.getenv('OPENREVIEW_BASEURL')
        or_user = os.getenv('OPENREVIEW_USERNAME')
        or_pw = os.getenv('OPENREVIEW_PASSWORD')
        TestRealDataset.client = openreview.Client(baseurl=or_baseurl, username=or_user, password=or_pw)


    @classmethod
    def tearDownClass(cls):
        pass

    # called at the beginning of each test
    # This uses the test_client() which builds the Flask app and runs it for testing.  It does not
    # start it in such a way that the app initializes correctly (i.e. by calling matcher/app.py) so
    # we have to set a couple things correctly
    def setUp (self):
        self.app = matcher.app.test_client()
        self.app.testing = True
        # Sets the webapp up so that it will switch to using the mock OR client
        # matcher.app.testing = True
        # Turn off logging in the web app so that tests run with a clean console
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True
        or_baseurl = os.getenv('OPENREVIEW_BASEURL')
        assert or_baseurl != None and or_baseurl != ''
        matcher.app.config['OPENREVIEW_BASEURL'] = or_baseurl
        # a map that keeps the status of all config-notes so that the test method knows when a config completes or fails
        matcher.app.running_configs = {}


    def tearDown (self):
        pass

    def _test_matcher (self, num_papers, num_reviewers, conflict_percentage=0, paper_min_reviewers=2, reviewer_max_papers=3,
                       custom_load_percentage=0, positive_constraint_percentage=0, negative_constraint_percentage=0):
        print("Testing")
        self.num_papers = num_papers
        self.num_reviewers = num_reviewers
        self.conf = TestConf(TestRealDataset.client,
                             num_papers = num_papers,
                             num_reviewers = num_reviewers,
                             conflict_percentage = conflict_percentage,
                             paper_min_reviewers = paper_min_reviewers,
                             reviewer_max_papers = reviewer_max_papers,
                             custom_load_percentage = custom_load_percentage,
                             positive_constraint_percentage = positive_constraint_percentage,
                             negative_constraint_percentage = negative_constraint_percentage)
        print("Testing Config " + self.conf.get_config_note_id())
        # Turn on logging in the web app because these are valid inputs and nothing should
        # go wrong in the app.  If it does, we want to see the errors in the console
        matcher.app.logger.disabled = False
        matcher.app.logger.parent.disabled = False
        matcher.app.running_configs[self.conf.get_config_note_id()] = Configuration.STATUS_INITIALIZED
        response = post_json(self.app, '/match', {'configNoteId': self.conf.get_config_note_id() },
                             headers={'Authorization': 'Bearer Valid'})
        print("Waiting for matcher to finish solving...")
        while matcher.app.running_configs[self.conf.get_config_note_id()] in [Configuration.STATUS_INITIALIZED, Configuration.STATUS_RUNNING]:
            pass
        print("Done!\n")
        del matcher.app.running_configs[self.conf.get_config_note_id()]
        assert response.status_code == 200

    def test_10papers_7reviewers (self):
        print("Testing with 10 papers, 7 reviewers")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test_10papers_7reviewers_100cust_loads (self):
        print("Testing with 10 papers, 7 reviewers, 100% custom loads")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, custom_load_percentage = 1)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_NO_SOLUTION)

    def test_10papers_7reviewers_25cust_loads (self):
        print("Testing with 10 papers, 7 reviewers, 25% custom loads")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, custom_load_percentage = 0.25)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_NO_SOLUTION)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test_10papers_7reviewers_75conflicts (self):
        print("Testing with 10 papers, 7 reviewers 75% conflicts")
        self._test_matcher(10, 7, conflict_percentage = 0.75, paper_min_reviewers = 2, reviewer_max_papers = 3)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)

    def test_10papers_7reviewers_25conflicts (self):
        print("Testing with 10 papers, 7 reviewers 25% conflicts")
        self._test_matcher(10, 7, conflict_percentage = 0.25, paper_min_reviewers = 2, reviewer_max_papers = 3)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test_10papers_7reviewers_100_neg_constraints (self):
        print("Testing with 10 papers, 7 reviewers 100% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 1)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)

    def test_10papers_7reviewers_10_neg_constraints (self):
        print("Testing with 10 papers, 7 reviewers 10% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.1)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)


    # 50% of the paper-reviewer combinations are vetoed and it still finds a match, but it does
    # find a relatively high-cost one (cost = -3246, whereas the cost of the unconstrained match is -4397)
    def test_10papers_7reviewers_50_neg_constraints (self):
        print("Testing with 10 papers, 7 reviewers 50% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.5)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test_10papers_7reviewers_70_neg_constraints (self):
        print("Testing with 10 papers, 7 reviewers 70% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.7)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)

    # A random 10% of the paper-reviewer combinations are locked and the cost of the assignment found (-4983) is better than
    # the cost of the solution found in the fully unconstrained match (-4397)
    # TODO:  This seems odd.  Why do we get a lower cost solution???
    def test_10papers_7reviewers_10_pos_constraints (self):
        print("Testing with 10 papers, 7 reviewers 10% positively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, positive_constraint_percentage = 0.1)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)


if __name__ == "__main__":
    unittest.main()