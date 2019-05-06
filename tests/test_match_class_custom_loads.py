import numpy as np
import pytest

from matcher.Encoder import Encoder
from matcher.fields import Configuration
from matcher.Match import Match
from helpers.Params import Params


# Note Well:  To run this test you must be running OR with a clean db.  See README for details.

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


    @pytest.mark.skip()
    # This test is not working.  The custom_load of 0 for reviewer 0 doesn't cause the matcher to omit using this reviewer in its solution.
    # Maybe we need a special case to add a constraint in the matrix if a load is zero????
    def test1_3papers_4reviewers_1custom_load (self, test_util):
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
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
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

        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert len(aggregate_score_edges) == num_reviewers * num_papers

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        enc = Encoder(config=test_util.get_conference().get_config_note().content)
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,enc)
        # Validate that the assignment edges are correct
        # reviewer-1 -> paper-1
        assert conference.get_assignment_edge(papers[1].id, reviewers[1]) != None
        # 2 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[2]) != None
        # 3 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[3]) != None
        # !reviewer-0 -> paper-0
        assert conference.get_assignment_edge(papers[0].id, reviewers[0]) == None


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
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
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

        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert len(aggregate_score_edges) == num_reviewers * num_papers

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()

        # Validate that the assignment edges are correct
        self.show_assignment(papers, conference)

        assert conference.get_assignment_edge(papers[1].id, reviewers[1]) != None
        assert conference.get_assignment_edge(papers[1].id, reviewers[2]) != None
        assert conference.get_assignment_edge(papers[1].id, reviewers[0]) == None
        assert conference.get_assignment_edge(papers[1].id, reviewers[3]) == None

        assert conference.get_assignment_edge(papers[2].id, reviewers[2]) != None
        assert conference.get_assignment_edge(papers[2].id, reviewers[3]) != None
        assert conference.get_assignment_edge(papers[2].id, reviewers[1]) == None
        assert conference.get_assignment_edge(papers[2].id, reviewers[0]) == None

        assert conference.get_assignment_edge(papers[0].id, reviewers[0]) != None
        assert conference.get_assignment_edge(papers[0].id, reviewers[1]) != None
        assert conference.get_assignment_edge(papers[0].id, reviewers[2]) == None
        assert conference.get_assignment_edge(papers[0].id, reviewers[3]) == None

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
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
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
        papers = conference.get_paper_notes()

        # Validate that the assignment edges are correct
        self.show_assignment(papers, conference)

        assert conference.get_assignment_edge(papers[0].id, reviewers[0]) != None
        assert conference.get_assignment_edge(papers[1].id, reviewers[4]) != None
        assert conference.get_assignment_edge(papers[2].id, reviewers[1]) != None
        assert conference.get_assignment_edge(papers[3].id, reviewers[3]) != None
        assert conference.get_assignment_edge(papers[4].id, reviewers[2]) != None

        assert conference.get_assignment_edge(papers[0].id, reviewers[1]) == None
        assert conference.get_assignment_edge(papers[0].id, reviewers[2]) == None
        assert conference.get_assignment_edge(papers[0].id, reviewers[3]) == None
        assert conference.get_assignment_edge(papers[0].id, reviewers[4]) == None
        assert conference.get_assignment_edge(papers[1].id, reviewers[0]) == None
        assert conference.get_assignment_edge(papers[1].id, reviewers[1]) == None
        assert conference.get_assignment_edge(papers[1].id, reviewers[2]) == None
        assert conference.get_assignment_edge(papers[1].id, reviewers[3]) == None
        assert conference.get_assignment_edge(papers[2].id, reviewers[0]) == None
        assert conference.get_assignment_edge(papers[2].id, reviewers[2]) == None
        assert conference.get_assignment_edge(papers[2].id, reviewers[3]) == None
        assert conference.get_assignment_edge(papers[2].id, reviewers[4]) == None
        assert conference.get_assignment_edge(papers[3].id, reviewers[0]) == None
        assert conference.get_assignment_edge(papers[3].id, reviewers[1]) == None
        assert conference.get_assignment_edge(papers[3].id, reviewers[2]) == None
        assert conference.get_assignment_edge(papers[3].id, reviewers[4]) == None
        assert conference.get_assignment_edge(papers[4].id, reviewers[0]) == None
        assert conference.get_assignment_edge(papers[4].id, reviewers[1]) == None
        assert conference.get_assignment_edge(papers[4].id, reviewers[3]) == None
        assert conference.get_assignment_edge(papers[4].id, reviewers[4]) == None


    # @pytest.mark.skip
    def test4_5papers_5reviewers_custom_loads (self, test_util):
        '''
        Reviewer 0 can only do 1 paper, but reviewer 1 can do 3, so result should make use of these
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
        num_reviews_per_paper = 2
        reviewer_max_papers = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_MAP: {0: 1, 1: 3}},
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
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

        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert len(aggregate_score_edges) == num_reviewers * num_papers

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()

        # Validate that the custom loads are respected
        self.show_assignment(papers, conference)

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
