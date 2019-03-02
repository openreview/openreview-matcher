import unittest
import json
import matcher
import os
import openreview
import time
import functools
from conference_config import TestConf
from matcher.fields import Configuration

def time_ms ():
    return int(round(time.time() * 1000))

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


    @classmethod
    def get_client(cls, base_url):
        client = openreview.Client(baseurl = base_url)
        assert client is not None, "Client is none"
        username = 'openreview.net'
        password = '1234'
        res = client.register_user(email = username, first = 'Super', last = 'User', password = password)
        assert res, "Res i none"
        res = client.activate_user('openreview.net', {
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
        group = client.get_group(id = 'openreview.net')
        assert group
        assert group.members == ['~Super_User1']

        # The matcher app config needs to know to use real openreview-py API and it needs the superuser
        # credentials created above
        matcher.app.config['TESTING'] = True
        matcher.app.config['USE_API'] = True
        matcher.app.config['OPENREVIEW_USERNAME'] = username
        matcher.app.config['OPENREVIEW_PASSWORD'] = password
        return client

    # called once at beginning of suite
    @classmethod
    def setUpClass(cls):
        or_baseurl = os.getenv('OPENREVIEW_BASEURL')
        TestRealDataset.client = TestRealDataset.get_client(or_baseurl)


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



    def tearDown (self):
        pass

    def _test_matcher(self, suffix_num, num_papers, num_reviewers, conflict_percentage=0, paper_min_reviewers=2,
                      reviewer_max_papers=3, custom_load_percentage=0, positive_constraint_percentage=0,
                      negative_constraint_percentage=0, custom_load_config={}):
        print("Running test", suffix_num)
        self.num_papers = num_papers
        self.num_reviewers = num_reviewers

        self.conf = TestConf(TestRealDataset.client,
                             suffix_num = suffix_num,
                             num_papers = num_papers,
                             num_reviewers = num_reviewers,
                             conflict_percentage = conflict_percentage,
                             paper_min_reviewers = paper_min_reviewers,
                             reviewer_max_papers = reviewer_max_papers,
                             custom_load_percentage = custom_load_percentage,
                             custom_load_config = custom_load_config,
                             positive_constraint_percentage = positive_constraint_percentage,
                             negative_constraint_percentage = negative_constraint_percentage
                             )
        config_id = self.conf.config_note_id
        print("Testing Config " + config_id)

        # Disable logging in the web app the test cases do the necessary result-checking when they expect
        # errors to happen inside the matcher.
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True
        response = post_json(self.app, '/match', {'configNoteId': self.conf.config_note_id },
                             headers={'Authorization': 'Bearer Valid'})
        print(time_ms(),"Waiting for matcher to finish solving...")
        # self.wait_until_complete(config_id)
        self.sleep_for_seconds(config_id, 5)
        assert response.status_code == 200

    def wait_until_complete(self, config_id):
        # stat = self.conf.get_config_note_status()
        stat = self.get_config_status(config_id)
        print("before waiting loop", stat)
        while stat in [Configuration.STATUS_INITIALIZED, Configuration.STATUS_RUNNING]:
            stat = self.get_config_status(config_id)
            print("loop: config note", self.conf.config_note_id, "status is", stat)
        print("After waiting:", stat, "Done!\n")

    def sleep_for_seconds(self, config_id, seconds):
        stat = self.get_config_status(config_id)
        print(time_ms(),"Before sleep", stat, "Config id:", config_id)
        time.sleep(seconds)
        print(time_ms(),"After sleep Config id:", config_id, "Status is now", stat)

    def get_config_status (self, config_id):
        config_note = TestRealDataset.client.get_note(config_id)
        return config_note.content['status']

    def _should_run(self, n):
        return type(self).active_test_flags.get(n, True) and type(self).active_test_flags[n]

    # Swap the two lines below and set flags to run individual tests.
    active_test_flags = { 1: False, 2: False, 3: False, 4: True, 5: False, 6: False, 7: False, 8: False, 9: False, 10: False }
    # active_test_flags = { 1: True, 2: True, 3: True, 4: True, 5: True, 6: True, 7: True, 8: True, 9: True, 10: True }

    # To look at the results of test1:
    # http://openreview.localhost/assignments?venue=FakeConferenceForTesting1.cc/2019/Conference
    # To login to OR when running test suite:  OpenReview.net / 1234 (as defined in get_client above)

    def test1_10papers_7reviewers (self):
        test_num = 1
        if not self._should_run(test_num):
            return

        num_papers = 10
        num_reviewers = 7
        reviews_needed_per_paper = 1
        reviewer_max_papers = 2
        print("\n\nTesting with {} papers, {} reviewers. \nEach paper needs at least {} review(s). \nEach reviewer must review {} paper(s)".
              format(num_papers, num_reviewers,reviews_needed_per_paper,reviewer_max_papers))
        try:
            self._test_matcher(test_num, num_papers, num_reviewers, paper_min_reviewers=reviews_needed_per_paper, reviewer_max_papers=reviewer_max_papers)
            config_stat = self.get_config_status(self.conf.config_note_id)
            assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
            assignment_notes = self.conf.get_assignment_notes()
            assert len(assignment_notes) == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(len(assignment_notes), self.num_papers)
        except Exception as exc:
            print("Something went wrong while running this test")
            print(exc)
            print('-------------------')
            raise exc
        finally:
            pass

    def get_review_supply (self, custom_loads):
        return functools.reduce(lambda x, value:x + value, custom_loads.values(), 0)

    def test2_10papers_7reviewers_5cust_load_5shortfall (self):
        test_num = 2
        if not self._should_run(test_num):
            return
        num_papers = 10
        num_reviewers = 7
        reviews_needed_per_paper = 2
        reviewer_max_papers = 3
        custom_load_config = {'load_reduction': 5}
        demand = num_papers*reviews_needed_per_paper
        supply = num_reviewers*reviewer_max_papers - custom_load_config['load_reduction']
        print("\n\nTesting with {} papers, {} reviewers. \nEach paper needs at least {} review(s).  \nTotal Demand: {}, Supply based on custom_loads: {}".format(num_papers, num_reviewers, reviews_needed_per_paper, demand, supply))
        try:
            self._test_matcher(test_num, num_papers, num_reviewers, paper_min_reviewers=reviews_needed_per_paper, reviewer_max_papers=reviewer_max_papers,
                               custom_load_config=custom_load_config)
            config_stat = self.get_config_status(self.conf.config_note_id)
            custom_loads = self.conf.get_custom_loads()
            review_supply = self.get_review_supply(custom_loads)
            assert config_stat == Configuration.STATUS_ERROR, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_ERROR)
            print("Got the expected error because supply<demand")

        except Exception as exc:
                print("Something went wrong while running this test")
                print(exc)
                print('-------------------')
                raise exc
        finally:
            pass


    def test3_10papers_7reviewers_0cust_load (self):
        test_num = 3
        if not self._should_run(test_num):
            return
        num_papers = 10
        num_reviewers = 7
        reviews_needed_per_paper = 2
        reviewer_max_papers = 3
        custom_load_config = {'load_reduction': 0} # need 10*2=20 reviews, no custom_loads will result in a 7*3=21 total
        demand = num_papers*reviews_needed_per_paper
        supply = num_reviewers*reviewer_max_papers - custom_load_config['load_reduction']
        print("\n\nTesting with {} papers, {} reviewers. \nEach paper needs at least {} review(s).  \nEach reviewers max paper(s) {}. \nSupply: {} Demand: {}".
              format(num_papers, num_reviewers,reviews_needed_per_paper,reviewer_max_papers, supply, demand))
        try:
            self._test_matcher(test_num, num_papers, num_reviewers, paper_min_reviewers=reviews_needed_per_paper, reviewer_max_papers=reviewer_max_papers,
                               custom_load_config=custom_load_config)
            config_stat = self.get_config_status(self.conf.config_note_id)
            assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_COMPLETE)
        except Exception as exc:
            print("Something went wrong while running this test")
            print(exc)
            print('-------------------')
            raise exc
        finally:
            pass


    def test4_10papers_7reviewers_5cust_load_excess (self):
        test_num = 4
        if not self._should_run(test_num):
            return
        num_papers = 10
        num_reviewers = 7
        reviews_needed_per_paper = 2
        reviewer_max_papers = 4
        custom_load_config = {'load_reduction': 5}
        demand = num_papers*reviews_needed_per_paper
        supply = num_reviewers*reviewer_max_papers - custom_load_config['load_reduction']
        print("\n\nTesting with {} papers, {} reviewers. \nEach paper needs at least {} review(s).  \nEach reviewers max paper(s) {}. \nSupply: {} Demand: {}".
              format(num_papers, num_reviewers,reviews_needed_per_paper,reviewer_max_papers, supply, demand))
        try:
            self._test_matcher(test_num, num_papers, num_reviewers, paper_min_reviewers=reviews_needed_per_paper, reviewer_max_papers=reviewer_max_papers,
                               custom_load_config=custom_load_config)
            config_stat = self.get_config_status(self.conf.config_note_id)
            assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_COMPLETE)
        except Exception as exc:
            print("Something went wrong while running this test")
            print(exc)
            print('-------------------')
            raise exc
        finally:
            pass

'''
    def test4_10papers_7reviewers_5cust_loads (self):
        test_num = 4
        if not self._should_run(test_num):
            return
        num_papers = 10
        num_reviewers = 7
        reviews_needed_per_paper = 2
        reviewer_max_papers = 4
        custom_load_percentage = 0.05
        print("\n\nTesting with {} papers, {} reviewers. \nEach paper needs at least {} review(s).  \nEach reviewer must review {} paper(s). \n{}% of reviewers have a custom_load below the min number of papers of reviewer should review".
              format(num_papers, num_reviewers,reviews_needed_per_paper,reviewer_max_papers, custom_load_percentage*100))
        try:
            self._test_matcher(test_num, num_papers, num_reviewers, paper_min_reviewers=reviews_needed_per_paper, reviewer_max_papers=reviewer_max_papers,
                               custom_load_percentage=custom_load_percentage*100)
            config_stat = self.get_config_status(self.conf.config_note_id)
            review_supply = self.conf.get_total_review_supply()
            if review_supply < num_papers * reviews_needed_per_paper:
                print("Expecting error because review supply", review_supply, "< demand", num_papers * reviews_needed_per_paper)
                assert config_stat == Configuration.STATUS_ERROR, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_ERROR)
            else:
                print("Expecting success because review supply", review_supply, ">= demand", num_papers * reviews_needed_per_paper)
                assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_NO_SOLUTION)
        except Exception as exc:
            print("Something went wrong while running this test")
            print(exc)
            print('-------------------')
            raise exc
        finally:
            pass

    # def test3_10papers_7reviewers_25cust_loads (self):
    #     if not self._should_run(3):
    #         return
    #     print("Testing with 10 papers, 7 reviewers, 25% custom loads")
    #     self._test_matcher(3, 10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, custom_load_percentage = 0.25)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {} expected {}".format(config_stat, Configuration.STATUS_NO_SOLUTION)
    #     num_assign_notes = self.conf.get_num_assignment_notes()
    #     assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)
    #
    # def test4_10papers_7reviewers_75conflicts (self):
    #     if not self._should_run(4):
    #         return
    #     print("Testing with 10 papers, 7 reviewers 75% conflicts")
    #     self._test_matcher(4, 10, 7, conflict_percentage = 0.75, paper_min_reviewers = 2, reviewer_max_papers = 3)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)
    #
    # def test5_10papers_7reviewers_25conflicts (self):
    #     if not self._should_run(5):
    #         return
    #     print("Testing with 10 papers, 7 reviewers 25% conflicts")
    #     self._test_matcher(5, 10, 7, conflict_percentage = 0.25, paper_min_reviewers = 2, reviewer_max_papers = 3)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
    #     num_assign_notes = self.conf.get_num_assignment_notes()
    #     assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)
    #
    # def test6_10papers_7reviewers_100_neg_constraints (self):
    #     if not self._should_run(6):
    #         return
    #     print("Testing with 10 papers, 7 reviewers 100% negatively constrained")
    #     self._test_matcher(6, 10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 1)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)
    #
    # def test7_10papers_7reviewers_10_neg_constraints (self):
    #     if not self._should_run(7):
    #         return
    #     print("Testing with 10 papers, 7 reviewers 10% negatively constrained")
    #     self._test_matcher(7, 10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.1)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
    #     num_assign_notes = self.conf.get_num_assignment_notes()
    #     assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)
    #
    #
    # # 50% of the paper-reviewer combinations are vetoed and it still finds a match, but it does
    # # find a relatively high-cost one (cost = -3246, whereas the cost of the unconstrained match is -4397)
    # def test8_10papers_7reviewers_50_neg_constraints (self):
    #     if not self._should_run(8):
    #         return
    #     print("Testing with 10 papers, 7 reviewers 50% negatively constrained")
    #     self._test_matcher(8, 10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.5)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
    #     num_assign_notes = self.conf.get_num_assignment_notes()
    #     assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)
    #
    # def test9_10papers_7reviewers_70_neg_constraints (self):
    #     if not self._should_run(9):
    #         return
    #     print("Testing with 10 papers, 7 reviewers 70% negatively constrained")
    #     self._test_matcher(9, 10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, negative_constraint_percentage = 0.7)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_NO_SOLUTION, "Failure: Config status is {}".format(config_stat)
    #
    # # A random 10% of the paper-reviewer combinations are locked and the cost of the assignment found (-4983) is better than
    # # the cost of the solution found in the fully unconstrained match (-4397)
    # # TODO:  This seems odd.  Why do we get a lower cost solution???
    # def test10_10papers_7reviewers_10_pos_constraints (self):
    #     if not self._should_run(10):
    #         return
    #     print("Testing with 10 papers, 7 reviewers 10% positively constrained")
    #     self._test_matcher(10, 10, 7, conflict_percentage = 0, paper_min_reviewers = 2, reviewer_max_papers = 3, positive_constraint_percentage = 0.1)
    #     config_stat = self.conf.get_config_note_status()
    #     assert config_stat == Configuration.STATUS_COMPLETE, "Failure: Config status is {}".format(config_stat)
    #     num_assign_notes = self.conf.get_num_assignment_notes()
    #     assert num_assign_notes == self.num_papers, "Number of assignments {} is not same as number of papers {}".format(num_assign_notes, self.num_papers)
    #
'''
if __name__ == "__main__":
    unittest.main()