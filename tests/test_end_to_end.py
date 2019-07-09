import matcher
import pytest
import time

from helpers.DisplayConf import DisplayConf
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges
from matcher.fields import Configuration
from helpers.Params import Params
from helpers.AssignmentChecker import AssignmentChecker

# Note Well:  To run this test you must be running OR with a clean db.  See README for details.
# End-to-end tests in this suite all build a conference using the test_util fixture passed to each test.
# This object builds a conference using edges to represent all the inputs to the matcher and then calls
# Flask endpoint to run the matcher.   Edge outputs of the matcher are then tested.

class TestEndToEnd():

    # called once at beginning of suite
    # See conftest.py for other run-once setup that is part of the test_util fixture passed to each test.
    @classmethod
    def setup_class(cls):

        # Turn off logging in the web app so that tests run with a clean console
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True
        cls.or_baseurl = 'http://localhost:3000'
        cls.silent = True
        assert cls.or_baseurl != None and cls.or_baseurl != ''
        # The flask test client does not start the matcher app in such a way that matcher/app.py runs
        # so this config option is set here
        matcher.app.config['OPENREVIEW_BASEURL'] = cls.or_baseurl

    @classmethod
    def teardown_class(cls):
        pass

    # called at the beginning of each test
    def setUp (self):
        print('-'*60)


    def tearDown (self):
        pass

    def test_10papers_7reviewers (self, test_util):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 3 reviews.
        Expects:  produce an assignment
        '''
        num_reviewers = 7
        num_papers = 10
        num_reviews_per_paper = 2
        params = Params({
             Params.NUM_PAPERS: num_papers,
             Params.NUM_REVIEWERS: num_reviewers,
             Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
             Params.REVIEWER_MAX_PAPERS: 3,
             }
        )
        test_util.set_test_params(params)
        try:
            test_util.test_matcher()
        except Exception as e:
            print(e)


        conference = test_util.get_conference() # type: ConferenceConfigWithEdges
        assert Configuration.STATUS_COMPLETE == conference.get_config_note_status(), \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assignment_edges = conference.get_assignment_edges()
        assert len(assignment_edges) == num_reviews_per_paper * len(conference.get_paper_notes()), \
            "Number of assignment edges {} is incorrect.  Should be". \
            format(len(assignment_edges), num_reviews_per_paper * len(conference.get_paper_notes()))


    # @pytest.mark.skip("Takes a LONG TIME!")
    def test_5000papers_2000reviewers (self, test_util):
        '''
        Tests 5000 papers each requiring 2 reviews.  2000 users each capable of giving 6 reviews.
        Expects:  produce an assignment
        '''
        num_reviews_per_paper = 2
        num_papers = 5000
        num_reviewers = 2000
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.SCORES_CONFIG: { Params.SCORE_TYPE: Params.RANDOM_SCORE,
                                                 Params.SCORE_INCREMENT: 0.01,
                                                 Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}}},
                         Params.REVIEWER_MAX_PAPERS: 6,
                         })
        test_util.set_test_params(params)
        now = time.time()
        test_util.build_conference()
        print("Time to build conference", time.time() - now)
        now = time.time()
        test_util.run_matcher()
        print("Time to run matcher", time.time() - now)
        conference = test_util.get_conference() # type: ConferenceConfigWithEdges
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assignment_edges = conference.get_assignment_edges()
        assert len(assignment_edges) == num_reviews_per_paper * len(conference.get_paper_notes()), \
            "Number of assignment edges {} is incorrect.  Should be". \
            format(len(assignment_edges), num_reviews_per_paper * len(conference.get_paper_notes()))


    def test_10papers_7reviewers_5cust_load_5shortfall (self, test_util):
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
        test_util.set_test_params(params)
        test_util.test_matcher()
        conference = test_util.get_conference() # type: ConferenceConfigWithEdges
        assert conference.get_config_note_status() == Configuration.STATUS_ERROR, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_ERROR)
        assert len(conference.get_assignment_edges()) == 0, "Assignment edges should not be created if match fails"

    def test_10papers_7reviewers_0cust_load (self, test_util):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 3 reviews.  Custom_loads will reduce supply by 0
        Expects:  Successful production of assignment
        '''
        num_papers = 10
        num_reviewers = 7
        num_revs_per_paper = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                  Params.NUM_REVIEWERS: num_reviewers,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_revs_per_paper,
                  Params.REVIEWER_MAX_PAPERS: 3,
                  Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_SUPPLY_DEDUCTION: 0}
            })
        test_util.set_test_params(params)
        test_util.test_matcher()
        conference = test_util.get_conference() # type: ConferenceConfigWithEdges
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert num_papers*num_revs_per_paper == len(conference.get_assignment_edges())
        custom_loads = conference.get_custom_loads()
        review_count_map = AssignmentChecker(conference).count_user_reviews()
        for reviewer, custom_load in custom_loads.items():
            assert review_count_map[reviewer] <= custom_load, "Reviewer " + reviewer + \
                " custom_load " +custom_load+ " exceeded.  Papers assigned: " + review_count_map[reviewer]

    def test_10papers_7reviewers_5cust_load_excess (self, test_util):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 4 reviews.  Custom_loads will reduce supply by 5
        Expects:  Successful production of assignment
        '''
        num_papers = 10
        num_reviewers = 7
        num_revs_per_paper = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                  Params.NUM_REVIEWERS: num_reviewers,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_revs_per_paper,
                  Params.REVIEWER_MAX_PAPERS: 4,
                  Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_SUPPLY_DEDUCTION: 5}
            })
        test_util.set_test_params(params)
        test_util.test_matcher()
        conference = test_util.get_conference() # type: ConferenceConfigWithEdges
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assert num_papers*num_revs_per_paper == len(conference.get_assignment_edges())
        custom_loads = conference.get_custom_loads()
        review_count_map = AssignmentChecker(conference).count_user_reviews()
        for reviewer, custom_load in custom_loads.items():
            assert review_count_map[reviewer] <= custom_load, "Reviewer " + reviewer + \
                " custom_load " +custom_load+ " exceeded.  Papers assigned: " + review_count_map[reviewer]


    def test_5papers_4reviewers_conflicts (self, test_util):
        '''
        Tests 5 papers each requiring 2 reviews.  4 users each capable of giving 3 reviews.  6 conflicts are created between papers/reviewers.
        Expects: Not sure if this should fail because of the number of conflicts limiting the supply significantly.
        '''
        num_papers = 5
        num_reviewers = 4
        num_revs_per_paper = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                  Params.NUM_REVIEWERS: num_reviewers,
                  Params.NUM_REVIEWS_NEEDED_PER_PAPER:num_revs_per_paper,
                  Params.REVIEWER_MAX_PAPERS: 3,
                  Params.CONFLICTS_CONFIG : {0: [1,2], 1: [1,2], 3: [3], 4: [3]}
            })

        test_util.set_test_params(params)
        test_util.test_matcher()

        conference = test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        conflicts = conference.get_conflicts()
        checker = AssignmentChecker(conference)
        for forum_id, reviewers in conflicts.items():
            for reviewer in reviewers:
                assert not checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                    "Reviewer {} has conflicts with paper {} but this pairing is found in the assignment".format(reviewer,forum_id)


    def test_5papers_4reviewers_conflicts (self, test_util):
        '''
        Tests 5 papers each requiring 2 reviews.  4 users each capable of giving 3 reviews.  3 conflicts are created between papers/reviewers.
        Expects: A successful match where conflicted users are not assigned to papers that they conflict with.
        '''
        num_papers = 5
        num_reviewers = 4
        num_revs_per_paper = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_revs_per_paper,
                         Params.REVIEWER_MAX_PAPERS: 3,
                         Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                         Params.CONFLICTS_CONFIG : {0: [0], 1: [1], 3: [3]}
                         })

        test_util.set_test_params(params)
        test_util.test_matcher()

        conference = test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        conflicts = conference.get_conflicts()
        checker = AssignmentChecker(conference)
        for forum_id, reviewers in conflicts.items():
            for reviewer in reviewers:
                assert not checker.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                    "Reviewer {} has conflicts with paper {} but this pairing is found in the assignment".format(reviewer,forum_id)
