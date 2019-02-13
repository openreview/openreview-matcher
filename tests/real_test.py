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

        supply = self.conf.get_total_review_supply()
        print("Review supply",supply)
        # Disable logging in the web app the test cases do the necessary result-checking when they expect
        # errors to happen inside the matcher.
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True
        matcher.app.running_configs[self.conf.get_config_note_id()] = Configuration.STATUS_INITIALIZED
        response = post_json(self.app, '/match', {'configNoteId': self.conf.get_config_note_id() },
                             headers={'Authorization': 'Bearer Valid'})
        print("Waiting for matcher to finish solving...")
        while matcher.app.running_configs[self.conf.get_config_note_id()] in [Configuration.STATUS_INITIALIZED, Configuration.STATUS_RUNNING]:
            pass
        print("Done!\n")
        del matcher.app.running_configs[self.conf.get_config_note_id()]
        assert response.status_code == 200


    def _should_run(self, n):
        return type(self).active_test_flags.get(n, True) and type(self).active_test_flags[n]

    # Swap the two lines below and set flags to run individual tests.
    # active_test_flags = { 1: False, 2: True, 3: False, 4: False, 5: False, 6: False, 7: False, 8: False, 9: False, 10: False }
    active_test_flags = { 1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: True, 8: True, 9: True, 10: True }

    # Each test below creates the conference objects necessary for a matcher run and then it runs the matcher.  Prior to each
    # test, conference objects are cleared from the db.   Therefore only the last test's objects will remain in the db when
    # the tests complete.   To look at a test result in the UI, it is best to use the active_test_flags above to turn off tests so that
    # just one runs.  Then view the configuration and its results in OR at:
    # http://openreview.localhost/assignments?venue=FakeConferenceForTesting.cc/2019/Conference


    def test1_10papers_7reviewers (self):
        if not self._should_run(1):
            return
        print("Testing with 10 papers, 7 reviewers")
        num_papers = 10
        reviews_needed_per_paper = 2
        self._test_matcher(num_papers, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test2_10papers_7reviewers_100cust_loads (self):
        if not self._should_run(2):
            return
        print("Testing with 10 papers, 7 reviewers, 100% custom loads")
        num_papers = 10
        reviews_needed_per_paper = 2
        self._test_matcher(num_papers, 7, conflict_percentage = 0, paper_min_reviewers = reviews_needed_per_paper, reviewer_max_papers = 3, custom_load_percentage = 1)
        config_stat = self.conf.get_config_note_status()
        review_supply = self.conf.get_total_review_supply()
        if review_supply < num_papers * reviews_needed_per_paper:
            assert config_stat == Configuration.STATUS_ERROR, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_ERROR)
        else:
            assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_NO_SOLUTION)

    def test3_10papers_7reviewers_25cust_loads (self):
        if not self._should_run(3):
            return
        print("Testing with 10 papers, 7 reviewers, 25% custom loads")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, custom_load_percentage = 0.25)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_NO_SOLUTION)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test4_10papers_7reviewers_75conflicts (self):
        if not self._should_run(4):
            return
        print("Testing with 10 papers, 7 reviewers 75% conflicts")
        self._test_matcher(10, 7, conflict_percentage = 0.75, paper_min_reviewers = 2, reviewer_max_papers = 3)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)

    def test5_10papers_7reviewers_25conflicts (self):
        if not self._should_run(5):
            return
        print("Testing with 10 papers, 7 reviewers 25% conflicts")
        self._test_matcher(10, 7, conflict_percentage = 0.25, paper_min_reviewers = 2, reviewer_max_papers = 3)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test6_10papers_7reviewers_100_neg_constraints (self):
        if not self._should_run(6):
            return
        print("Testing with 10 papers, 7 reviewers 100% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 1)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)

    def test7_10papers_7reviewers_10_neg_constraints (self):
        if not self._should_run(7):
            return
        print("Testing with 10 papers, 7 reviewers 10% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.1)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)


    # 50% of the paper-reviewer combinations are vetoed and it still finds a match, but it does
    # find a relatively high-cost one (cost = -3246, whereas the cost of the unconstrained match is -4397)
    def test8_10papers_7reviewers_50_neg_constraints (self):
        if not self._should_run(8):
            return
        print("Testing with 10 papers, 7 reviewers 50% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.5)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)

    def test9_10papers_7reviewers_70_neg_constraints (self):
        if not self._should_run(9):
            return
        print("Testing with 10 papers, 7 reviewers 70% negatively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.7)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)

    # A random 10% of the paper-reviewer combinations are locked and the cost of the assignment found (-4983) is better than
    # the cost of the solution found in the fully unconstrained match (-4397)
    # TODO:  This seems odd.  Why do we get a lower cost solution???
    def test10_10papers_7reviewers_10_pos_constraints (self):
        if not self._should_run(10):
            return
        print("Testing with 10 papers, 7 reviewers 10% positively constrained")
        self._test_matcher(10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, positive_constraint_percentage = 0.1)
        config_stat = self.conf.get_config_note_status()
        assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
        num_assign_notes = self.conf.get_num_assignment_notes()
        assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)


if __name__ == "__main__":
    unittest.main()