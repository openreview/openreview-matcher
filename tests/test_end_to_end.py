import unittest
import matcher
import os

from helpers.display_conf import DisplayConf
from matcher.fields import Configuration
from params import Params
from helpers.test_util import TestUtil
from helpers.assignment_checker import AssignmentChecker

# Note Well:  To run this test you must be running OR with a clean db.  See README for details.

class TestEndToEnd(unittest.TestCase):

    # called once at beginning of suite
    @classmethod
    def setUpClass(cls):
        # Flask provides a test client so that endpoints of the matcher app can be called directly and given inputs exactly as
        # they would in the field.
        cls.flask_app_test_client = matcher.app.test_client()
        cls.flask_app_test_client.testing = True

        # Turn off logging in the web app so that tests run with a clean console
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True
        cls.or_baseurl = os.getenv('OPENREVIEW_BASEURL')
        assert cls.or_baseurl != None and cls.or_baseurl != ''
        # The flask test client does not start the matcher app in such a way that matcher/app.py runs
        # so this config option is set here
        matcher.app.config['OPENREVIEW_BASEURL'] = cls.or_baseurl

        cls.silent = True # shut off all printing
        cls.test_util = TestUtil.get_instance(TestEndToEnd.or_baseurl, TestEndToEnd.flask_app_test_client, silent=cls.silent)


    @classmethod
    def tearDownClass(cls):
        pass

    # called at the beginning of each test
    def setUp (self):
        print('-'*60)


    def tearDown (self):
        pass


    # @unittest.skip
    def test1_10papers_7reviewers (self):
        '''
        Tests 10 papers each requiring 1 review.  7 users each capable of giving 2 reviews.
        Expects:  produce an assignment
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                  Params.REVIEWER_MAX_PAPERS: 2,
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), "Number of assignments {} is not same as number of papers {}". \
            format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))

    # @unittest.skip
    def test2_10papers_7reviewers_5cust_load_5shortfall (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 3 reviews.  Custom_loads will reduce supply by 5
        Expects:  Failure because supply (16) < demand (20)
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 3,
                  Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_SUPPLY_DEDUCTION: 5}
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_ERROR, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_ERROR)
        assert len(conference.get_assignment_notes()) == 0, "Assignment notes should not be created if match fails"


    # @unittest.skip
    def test3_10papers_7reviewers_0cust_load (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 3 reviews.  Custom_loads will reduce supply by 0
        Expects:  Successful production of assignment
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 3,
                  Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_SUPPLY_DEDUCTION: 0}
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))
        custom_loads = conference.get_custom_loads()
        review_count_map = AssignmentChecker(conference).count_user_reviews()
        for reviewer, custom_load in custom_loads.items():
            assert review_count_map[reviewer] <= custom_load, "Reviewer " + reviewer + \
                " custom_load " +custom_load+ " exceeded.  Papers assigned: " + review_count_map[reviewer]


    # @unittest.skip
    def test4_10papers_7reviewers_5cust_load_excess (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Custom_loads will reduce supply by 5
        Expects:  Successful production of assignment
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_SUPPLY_DEDUCTION: 5}
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))
        custom_loads = conference.get_custom_loads()
        review_count_map = AssignmentChecker(conference).count_user_reviews()
        for reviewer, custom_load in custom_loads.items():
            assert review_count_map[reviewer] <= custom_load, "Reviewer " + reviewer + \
                " custom_load " +custom_load+ " exceeded.  Papers assigned: " + review_count_map[reviewer]

    # @unittest.skip
    def test5_10papers_7reviewers_4locks (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Constraints lock in users to 4 papers
        Expects:  Successful production of assignment where locked user are assigned to the papers they are locked to.
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  # paper indices mapped to reviewer indices to indicate lock of the pair
                  Params.CONSTRAINTS_CONFIG: {
                      Params.CONSTRAINTS_LOCKS: {0: [4], 2: [4], 4: [1], 5: [1]}
                  }
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))

        constraints = conference.get_constraints()
        checker = AssignmentChecker(conference)
        for forum_id, reviewer_dict in constraints.items():
            for reviewer, val in reviewer_dict.items():
                if val == Configuration.LOCK:
                    assert checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                        "Reviewer {} was locked to paper {} by constraint but not found in assignment".format(reviewer,forum_id)


    # @unittest.skip
    def test6_10papers_7reviewers_8vetos (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Constraints veto users in 4 papers
        Expects:  Successful production of assignment where vetoed users do are not assigned to papers they were vetoed from.
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  # paper indices mapped to reviewer indices to indicate veto of the pair
                  Params.CONSTRAINTS_CONFIG: {
                      Params.CONSTRAINTS_VETOS : {0: [1,2], 1: [1,2], 2: [1,2,3], 3: [5]}
                  }
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))

        constraints = conference.get_constraints()
        try:
            checker = AssignmentChecker(conference)
            for forum_id, reviewer_dict in constraints.items():
                for reviewer, val in reviewer_dict.items():
                    if val == Configuration.VETO:
                        assert not checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                            "Reviewer {} was vetoed from paper {} by constraint but this pairing is found in assignment".format(reviewer,forum_id)
        except AssertionError as exc:
            DisplayConf(conference, self.silent).show_assignment()
            raise exc

    # @unittest.skip
    def test7_10papers_7reviewers_3vetos (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Constraints veto users in 3 papers
        Expects:  Successful production of assignment where vetoed users do are not assigned to papers they were vetoed from.
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  # paper indices mapped to reviewer indices to indicate veto of the pair
                  Params.CONSTRAINTS_CONFIG: {
                      Params.CONSTRAINTS_VETOS : {0: [0], 1: [1], 2: [2]}
                  }
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))

        constraints = conference.get_constraints()
        try:
            checker = AssignmentChecker(conference)
            for forum_id, reviewer_dict in constraints.items():
                for reviewer, val in reviewer_dict.items():
                    if val == Configuration.VETO:
                        assert not checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                            "Reviewer {} was vetoed from paper {} by constraint but this pairing is found in assignment".format(reviewer,forum_id)
        except AssertionError as exc:
            DisplayConf(conference, self.silent).show_assignment()
            raise exc

    # @unittest.skip
    def test8_10papers_7reviewers_3locks (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Constraints lock users in 2 papers
        Expects:  Successful production of assignment where locked users are assigned to papers they were locked to.
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  # paper indices mapped to reviewer indices to indicate lock of the pair
                  Params.CONSTRAINTS_CONFIG: {
                      Params.CONSTRAINTS_LOCKS : {0: [0], 1: [1,2]}
                  }
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))

        constraints = conference.get_constraints()
        checker = AssignmentChecker(conference)
        for forum_id, reviewer_dict in constraints.items():
            for reviewer, val in reviewer_dict.items():
                if val == Configuration.LOCK:
                    assert checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                        "Reviewer {} was locked to paper {} by constraint but not found in assignment".format(reviewer,forum_id)


    # @unittest.skip
    def test9_10papers_7reviewers_10locks (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Constraints lock users in all 10 papers
        Expects:  Successful production of assignment where locked users are assigned to papers they were locked to.
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  # paper indices mapped to reviewer indices to indicate lock of the pair
                  Params.CONSTRAINTS_CONFIG: {
                      Params.CONSTRAINTS_LOCKS : {0:[0], 1:[1], 2:[2], 3:[3], 4:[4], 5:[5], 6:[6], 7:[0], 8:[1], 9:[2]}
                  }
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))

        constraints = conference.get_constraints()
        try:
            checker = AssignmentChecker(conference)
            for forum_id, reviewer_dict in constraints.items():
                for reviewer, val in reviewer_dict.items():
                    if val == Configuration.LOCK:
                        assert checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                            "Reviewer {} was locked to paper {} by constraint but not found in assignment".format(reviewer,forum_id)
        except AssertionError as exc:
            DisplayConf(conference, self.silent).show_assignment()
            raise exc

    # @unittest.skip
    def test10_10papers_7reviewers_4vetos_8locks (self):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Constraints veto users in 4 papers and lock users in 4 papers
        Expects:  Successful production of assignment where locked users are assigned to papers they were locked to and vetoed users are not assigned to papers they were vetoed from.
        '''
        params = Params({Params.NUM_PAPERS: 10,
                  Params.NUM_REVIEWERS: 7,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  Params.CONSTRAINTS_CONFIG: {
                      Params.CONSTRAINTS_VETOS : {0: [1,2], 1: [1,2], 2: [1,2,3], 3: [5]},
                      Params.CONSTRAINTS_LOCKS: {0: [4], 2: [4], 4: [1], 5: [1]}
                  }
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()
        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert len(conference.get_assignment_notes()) == len(conference.get_paper_notes()), \
            "Number of assignments {} is not same as number of papers {}". \
                format(len(conference.get_assignment_notes()), len(conference.get_paper_notes()))

        constraints = conference.get_constraints()
        try:
            checker = AssignmentChecker(conference)
            for forum_id, reviewer_dict in constraints.items():
                for reviewer, val in reviewer_dict.items():
                    if val == Configuration.LOCK:
                        assert checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                            "Reviewer {} was locked to paper {} by constraint but not found in assignment".format(reviewer,forum_id)
                    elif val == Configuration.VETO:
                        assert not checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                            "Reviewer {} was vetoed from paper {} by constraint but this pairing is found in the assignment".format(reviewer,forum_id)
        except AssertionError as exc:
            DisplayConf(conference, self.silent).show_assignment()
            raise exc

    # @unittest.skip
    def test11_5papers_4reviewers_conflicts (self):
        '''
        Tests 5 papers each requiring 2 reviews.  4 users each capable of giving 3 reviews.  6 conflicts are created between papers/reviewers.
        Expects: Not sure if this should fail because of the number of conflicts limiting the supply significantly.
        '''
        params = Params({Params.NUM_PAPERS: 5,
                  Params.NUM_REVIEWERS: 4,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                  Params.REVIEWER_MAX_PAPERS: 3,
                  Params.CONFLICTS_CONFIG : {0: [1,2], 1: [1,2], 3: [3], 4: [3]}
            })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()

        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        conflicts = conference.get_conflicts()
        try:
            checker = AssignmentChecker(conference)
            for forum_id, reviewers in conflicts.items():
                for reviewer in reviewers:
                   assert not checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                        "Reviewer {} has conflicts with paper {} but this pairing is found in the assignment".format(reviewer,forum_id)
        except AssertionError as exc:
            DisplayConf(conference, self.silent).show_assignment()
            raise exc

    # @unittest.skip
    def test12_5papers_4reviewers_conflicts (self):
        '''
        Tests 5 papers each requiring 2 reviews.  4 users each capable of giving 3 reviews.  3 conflicts are created between papers/reviewers.
        Expects: A successful match where conflicted users are not assigned to papers that they conflict with.
        '''
        params = Params({Params.NUM_PAPERS: 5,
                         Params.NUM_REVIEWERS: 4,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                         Params.REVIEWER_MAX_PAPERS: 3,
                         Params.CONFLICTS_CONFIG : {0: [0], 1: [1], 3: [3]}
                         })
        self.test_util.set_test_params(params)
        self.test_util.test_matcher()

        conference = self.test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        conflicts = conference.get_conflicts()
        try:
            checker = AssignmentChecker(conference)
            for forum_id, reviewers in conflicts.items():
                for reviewer in reviewers:
                    assert not checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                        "Reviewer {} has conflicts with paper {} but this pairing is found in the assignment".format(reviewer,forum_id)
        except AssertionError as exc:
            DisplayConf(conference, self.silent).show_assignment()
            raise exc



if __name__ == "__main__":
    unittest.main()