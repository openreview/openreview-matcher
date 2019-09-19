import numpy as np
import pytest

from matcher.fields import Configuration
from matcher.Match import Match
from helpers.Params import Params
from helpers.AssignmentChecker import AssignmentChecker

# Verifies that custom loads are being used correctly in the matcher.  Each unit test uses the test_util fixture to build a conference
# and the matcher is called to find a solution.  We then check the solution to make sure custom_loads were not violated.
# Note Well:  To run this test you must be running OR with a clean db.  See README for details.

#TODO These tests may fail now because custom_load invitation is now validated by the server and will need to have the type of its
# head object be a configuration Note.

class TestMatchClassCustomLoads():

    # called once at beginning of suite
    # See conftest.py for other run-once setup that is part of the test_util fixture passed to each test.
    @classmethod
    def setup_class(cls):
        cls.silent = True

    @classmethod
    def teardown_class(cls):
        pass

    # called at the beginning of each test
    def setUp (self):
        print('-'*60)


    def tearDown (self):
        pass


    # @pytest.mark.skip("test fails")
    # This test is not working.  The custom_load of 0 for reviewer 0 doesn't cause the matcher to omit using this reviewer in its solution.
    # The zero is sent to the solver in the list of minimums but it doesn't heed it.
    def test_custom_load_is_zero (self, test_util):
        '''
        Reviewer 0 has a custom_load of 0 and cannot review paper 0 despite being the high scorer.
        :param test_util:
        :return:
        '''
        score_matrix = np.array([
            [10.67801, 0, 0],
            [0, 10.67801, 0],
            [0, 0, 10.67801],
            [0, 0, 10.67801]
        ])
        num_papers = 3
        num_reviewers = 4
        num_reviews_per_paper = 2
        reviewer_max_papers = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_MAP: {0: 0, 1: 2}},
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })

        test_util.set_test_params(params)
        test_util.build_conference()
        match = Match(test_util.client, test_util.get_conference().get_config_note())
        match.compute_match()
        conference = test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assignment_edges = conference.get_assignment_edges()
        assert len(assignment_edges) == num_reviews_per_paper * len(conference.get_paper_notes()), "Number of assignment edges {} is incorrect.  Should be". \
            format(len(assignment_edges), num_reviews_per_paper * len(conference.get_paper_notes()))

        paper_ids = conference.get_paper_note_ids()
        reviewers = conference.reviewers
        c = AssignmentChecker(conference)
        assert c.is_paper_assigned_to_reviewer(paper_ids[1], reviewers[1])
        assert c.is_paper_assigned_to_reviewer(paper_ids[2], reviewers[2])
        assert c.is_paper_assigned_to_reviewer(paper_ids[2], reviewers[3])
        assert not c.is_paper_assigned_to_reviewer(paper_ids[0], reviewers[0])
        assert not c.is_paper_assigned_to_reviewer(paper_ids[1], reviewers[0])
        assert not c.is_paper_assigned_to_reviewer(paper_ids[2], reviewers[0])
        # paper 0 gets 2 reviews from among reviewers 1,2,3
        assert c.count_reviewers_assigned_to_paper(paper_ids[0], reviewers[1:]) == 2
        # paper 1 gets 2 reviews from among reviewers 0,1,2,3
        assert c.count_reviewers_assigned_to_paper(paper_ids[1], reviewers) == 2
        # paper 2 gets 2 reviews from among reviewers 0,1,2,3
        assert c.count_reviewers_assigned_to_paper(paper_ids[2], reviewers) == 2


    # @pytest.mark.skip()
    def test2_3papers_4reviewers_1custom_load (self, test_util):
        '''
        Reviewer 0 has a custom_load of 1 and cannot be the second reviewer of paper 1
        :param test_util:
        :return:
        '''
        score_matrix = np.array([
            [10.67801, 3, 0],
            [0, 10.67801, 0],
            [0, 0, 10.67801],
            [0, 0, 10.67801]
        ])
        num_papers = 3
        num_reviewers = 4
        num_reviews_per_paper = 2
        reviewer_max_papers = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_MAP: {0: 1, 1: 2}},
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })

        test_util.set_test_params(params)
        test_util.build_conference()
        match = Match(test_util.client, test_util.get_conference().get_config_note())
        match.compute_match()
        conference = test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assignment_edges = conference.get_assignment_edges()
        assert len(assignment_edges) == num_reviews_per_paper * len(conference.get_paper_notes()), "Number of assignment edges {} is incorrect.  Should be". \
            format(len(assignment_edges), num_reviews_per_paper * len(conference.get_paper_notes()))

        paper_ids = conference.get_paper_note_ids()
        reviewers = conference.reviewers
        c = AssignmentChecker(conference)
        assert c.is_paper_assigned_to_reviewer(paper_ids[0], reviewers[0])
        assert c.is_paper_assigned_to_reviewer(paper_ids[0], reviewers[1])
        assert c.is_paper_assigned_to_reviewer(paper_ids[1], reviewers[1])
        assert c.is_paper_assigned_to_reviewer(paper_ids[1], reviewers[2])
        assert c.is_paper_assigned_to_reviewer(paper_ids[2], reviewers[2])
        assert c.is_paper_assigned_to_reviewer(paper_ids[2], reviewers[3])


    # @pytest.mark.skip()
    def test3_5papers_5reviewers_custom_loads (self, test_util):
        '''
        Sanity check to make sure the correct solution is found
        :param test_util:
        :return:
        '''
        score_matrix = np.array([
            [10.67801, 0,0,0, 0],
            [0,0, 10.67801, 0,0],
            [0, 0, 0,0, 10.67801],
            [0, 0, 0, 10.67801, 0],
            [0, 10.67801, 0,0,0]
        ])
        num_papers = 5
        num_reviewers = 5
        num_reviews_per_paper = 1
        reviewer_max_papers = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })

        test_util.set_test_params(params)
        test_util.build_conference()
        match = Match(test_util.client, test_util.get_conference().get_config_note())
        match.compute_match()
        conference = test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assignment_edges = conference.get_assignment_edges()
        assert len(assignment_edges) == num_reviews_per_paper * len(conference.get_paper_notes()), "Number of assignment edges {} is incorrect.  Should be". \
            format(len(assignment_edges), num_reviews_per_paper * len(conference.get_paper_notes()))
        paper_ids = conference.get_paper_note_ids()
        reviewers = conference.reviewers
        c = AssignmentChecker(conference)
        assert c.is_paper_assigned_to_reviewer(paper_ids[0], reviewers[0])
        assert c.is_paper_assigned_to_reviewer(paper_ids[1], reviewers[4])
        assert c.is_paper_assigned_to_reviewer(paper_ids[2], reviewers[1])
        assert c.is_paper_assigned_to_reviewer(paper_ids[3], reviewers[3])
        assert c.is_paper_assigned_to_reviewer(paper_ids[4], reviewers[2])


    # @pytest.mark.skip
    def test4_5papers_5reviewers_custom_loads (self, test_util):
        '''
        Reviewer 0 can only do 1 paper, but reviewer 1 can do 3, so result should make use of these
        :param test_util:
        :return:
        '''
        score_matrix = np.array([
            [10.67801, 0, 0, 0, 0],
            [0, 0, 10.67801, 0, 0],
            [0, 0, 0, 0, 10.67801],
            [0, 0, 0, 10.67801, 0],
            [0, 10.67801, 0, 0, 0]
        ])
        num_papers = 5
        num_reviewers = 5
        num_reviews_per_paper = 2
        reviewer_max_papers = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_MAP: {0: 1, 1: 3}},
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })

        test_util.set_test_params(params)
        test_util.build_conference()
        match = Match(test_util.client, test_util.get_conference().get_config_note())
        match.compute_match()
        conference = test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assignment_edges = conference.get_assignment_edges()
        assert len(assignment_edges) == num_reviews_per_paper * len(conference.get_paper_notes()), "Number of assignment edges {} is incorrect.  Should be". \
            format(len(assignment_edges), num_reviews_per_paper * len(conference.get_paper_notes()))

        reviewers = conference.reviewers

        assert len(conference.get_assignment_edges_by_reviewer(reviewers[0])) == 1
        assert len(conference.get_assignment_edges_by_reviewer(reviewers[1])) == 3
        assert len(conference.get_assignment_edges_by_reviewer(reviewers[2])) == 2
        assert len(conference.get_assignment_edges_by_reviewer(reviewers[3])) == 2
        assert len(conference.get_assignment_edges_by_reviewer(reviewers[4])) == 2

    def show_assignment (self, papers, conference):
        edges = conference.get_assignment_edges()
        for e in edges:
            forum_id = e.head
            rev = e.tail
            title = list(filter(lambda x: x.id==forum_id, papers))[0].content['title']
            print(rev, '->', title)
