import numpy as np
import pytest
from exc.exceptions import NotFoundError
from matcher.Match import Match
from matcher.fields import Configuration
from matcher.PaperUserScores import PaperUserScores
from helpers.Params import Params

# Unit tests that make sure that aggregate score edges are correctly produced when a match is run.
#  Each test uses the test_util fixture to build a conference.  We directly access the Matcher object
# to run the matcher.  To test, we then create an encoder object and use it to compute the aggregate score of each paper/reviewer
# and then verify that an aggregate_score edge was produced with that value.
# N.B.:  To run this test you must be running OR with a clean db.  See README for details.
class TestMatchClassAggregateScores():
    bid_translate_map = {
        'low': 0.2,
        'medium': 0.5,
        'high': 0.8,
        'very high': 0.9,
    }


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



    def make_entry_from_edges (self, score_edges):
        entry = {}
        for e in score_edges:
            score_name = e.invitation.split('/')[-1]
            entry[score_name] = e.weight
        return entry

    # verify aggregate score edges have values that are correct
    def check_aggregate_score_edges(self, client, num_alternates, conference, paper_reviewer_data, assignment_edges):
        agg_score_inv_id = conference.conf_ids.AGGREGATE_SCORE_ID
        # first verify that there is an aggregate score edge for every assigned paper-reviewer
        for e in assignment_edges:
            paper_user_scores = paper_reviewer_data.get_entry(e.head, e.tail)
            agg_score = paper_user_scores.aggregate_score
            ag_sc_edge = client.get_edges(invitation=agg_score_inv_id, head=e.head, tail=e.tail)[0]
            assert ag_sc_edge.weight == agg_score
        # verify that we get each paper's top N alternates that are not assigned
        for forum_id, reviewers in paper_reviewer_data.items():
            count = 0
            scores = list(reviewers.values())
            scores.sort(reverse=True)
            for paper_user_scores in scores: #type: PaperUserScores
                if count == num_alternates:
                    break
                if not self.in_assignment(forum_id, paper_user_scores.user, assignment_edges):
                    count += 1
                    ag_sc_edge = client.get_edges(invitation=agg_score_inv_id, head=forum_id, tail=paper_user_scores.user)[0]
                    assert ag_sc_edge.weight == paper_user_scores.aggregate_score

    def in_assignment (self, forum_id, user, assignment_edges):
        for e in assignment_edges:
            if e.head==forum_id and e.tail==user:
                return True
        return False


    def expected_number_of_aggregate_score_edges (self, num_papers, num_reviewers, num_alternates, num_reviews_per_paper):
        return num_papers*num_reviews_per_paper + num_papers*min(num_alternates,num_reviewers-num_reviews_per_paper)


    # @pytest.mark.skip
    def test1_10papers_7reviewers (self, test_util):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 3 reviews.
        Validates that the output aggregate score edges are correct with respect to the paper-reviewer scores input
        '''
        num_papers = 10
        num_reviewers = 7
        num_reviews_per_paper = 2
        alternates = 10

        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.ALTERNATES: alternates,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: 3,
                         Params.SCORES_CONFIG: { Params.SCORE_TYPE: Params.INCREMENTAL_SCORE,
                                                 Params.SCORE_INCREMENT: 0.01,
                                                 Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}}}
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

        expected_agg_edges = self.expected_number_of_aggregate_score_edges(num_papers,num_reviewers,alternates,num_reviews_per_paper)
        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert expected_agg_edges == len(aggregate_score_edges)
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client, alternates, conference, paper_reviewer_data, assignment_edges)



    # @pytest.mark.skip
    def test2_3papers_4reviewers (self, test_util):
        '''
        Validates that the output aggregate score edges are correct with respect to the paper-reviewer scores input
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
        alternates = 3 # Will only be able to assign 2 because there are 4 reviewers, 2 of which will be assigned
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.ALTERNATES: alternates,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })

        test_util.set_test_params(params)
        test_util.build_conference()
        test_util.enable_logging()
        match = Match(test_util.client, test_util.get_conference().get_config_note())
        match.compute_match()
        conference = test_util.get_conference()
        assert conference.get_config_note_status() == Configuration.STATUS_COMPLETE, \
            "Failure: Config status is {} expected {}".format(conference.get_config_note_status(), Configuration.STATUS_COMPLETE)
        assignment_edges = conference.get_assignment_edges()
        assert len(assignment_edges) == num_reviews_per_paper * len(conference.get_paper_notes()), "Number of assignment edges {} is incorrect.  Should be". \
            format(len(assignment_edges), num_reviews_per_paper * len(conference.get_paper_notes()))
        expected_agg_edges = self.expected_number_of_aggregate_score_edges(num_papers,num_reviewers,alternates,num_reviews_per_paper)
        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert expected_agg_edges == len(aggregate_score_edges)

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client, alternates, conference, paper_reviewer_data, assignment_edges)
        # Validate that the assignment edges are correct
        # reviewer-0 -> paper-0
        assert conference.get_assignment_edge(papers[0].id, reviewers[0]) != None
        # reviewer-1 -> paper-1
        assert conference.get_assignment_edge(papers[1].id, reviewers[1]) != None
        # 2 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[2]) != None
        # 3 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[3]) != None

    # @pytest.mark.skip
    def test3_3papers_4reviewers_1conflict (self, test_util):
        '''
        Paper 0 conflicts with Reviewer 0 so this cannot be in the solution.
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
        alternates = 1
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.ALTERNATES: alternates,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CONFLICTS_CONFIG: {0: [0]},
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

        expected_agg_edges = self.expected_number_of_aggregate_score_edges(num_papers,num_reviewers,alternates,num_reviews_per_paper)
        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert expected_agg_edges == len(aggregate_score_edges)

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client, alternates, conference, paper_reviewer_data, assignment_edges)
        # Validate that the assignment edges are correct
        # reviewer-1 -> paper-1
        assert conference.get_assignment_edge(papers[1].id, reviewers[1]) != None
        # 2 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[2]) != None
        # 3 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[3]) != None

        # !reviewer-0 -> paper-0
        try:
            conference.get_assignment_edge(papers[0].id, reviewers[0])
        except NotFoundError:
            assert True


    @pytest.mark.skip("Lock/veto constraints no longer supported")
    def test4_3papers_4reviewers_1conflict (self, test_util):
        '''
        Paper 0 conflicts with Reviewer 0 so this cannot be in the solution.
        But Reviewer 0 is locked to Paper 0 so the constraint wins.
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
        alternates = 1
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.ALTERNATES: alternates,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CONFLICTS_CONFIG: {0: [0]},
                         Params.CONSTRAINTS_CONFIG: {Params.CONSTRAINTS_LOCKS: {0: [0]}},
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

        expected_agg_edges = self.expected_number_of_aggregate_score_edges(num_papers,num_reviewers,alternates,num_reviews_per_paper)
        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert expected_agg_edges == len(aggregate_score_edges)

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client, alternates, conference, paper_reviewer_data, assignment_edges)
        # Validate that the assignment edges are correct
        # reviewer-1 -> paper-1
        assert conference.get_assignment_edge(papers[1].id, reviewers[1]) != None
        # 2 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[2]) != None
        # 3 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[3]) != None
        # !reviewer-0 -> paper-0
        assert conference.get_assignment_edge(papers[0].id, reviewers[0]) != None


    # @pytest.mark.skip()
    def test_aggregate_score_with_missing_score (self, test_util):
        '''
        Is the same as test4 above but it deletes all the edges created from the 0's in the score_matrix which sets up the test case.
        This will test the matcher's ability to use a default when no score is present in the configuration.
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
        alternates = 5 # can only assign 2 as alternates
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.ALTERNATES: alternates,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.OMIT_ZERO_SCORE_EDGES: True,
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

        expected_agg_edges = self.expected_number_of_aggregate_score_edges(num_papers,num_reviewers,alternates,num_reviews_per_paper)
        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert expected_agg_edges == len(aggregate_score_edges)

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client, alternates, conference, paper_reviewer_data, assignment_edges)
        # Validate that the assignment edges are correct
        # reviewer-1 -> paper-1
        assert conference.get_assignment_edge(papers[1].id, reviewers[1]) != None
        # 2 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[2]) != None
        # 3 -> 2
        assert conference.get_assignment_edge(papers[2].id, reviewers[3]) != None
        # !reviewer-0 -> paper-0
        assert conference.get_assignment_edge(papers[0].id, reviewers[0]) != None

    # @pytest.mark.skip("not sure this still builds correct setup omitting edges and bid needs to be symbolic")
    def test_aggregate_with_missing_scores (self, test_util):
        '''
        Three scores are used but no user will provide them.
        This will test the matcher's ability to use a default when no score is present in the configuration.
        :param test_util:
        :return:
        '''
        num_papers = 3
        num_reviewers = 4
        num_reviews_per_paper = 2
        reviewer_max_papers = 2
        alternates = 1
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.ALTERNATES: alternates,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.SCORES_CONFIG: {
                                                Params.SCORES_SPEC: {
                                                    'affinity': {'weight': 1, 'default': 0},
                                                    'recommendation': {'weight': 1, 'default': 0},
                                                    'bid': {'weight': 1, 'default': 0.3, 'translate_map': self.bid_translate_map}
                                                },
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.OMIT_ZERO_SCORE_EDGES: True,
                                                Params.FIXED_SCORE_VALUE: {'affinity': 0, 'recommendation': 0, 'bid': 'low'}
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

        expected_agg_edges = self.expected_number_of_aggregate_score_edges(num_papers,num_reviewers,alternates,num_reviews_per_paper)
        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert expected_agg_edges == len(aggregate_score_edges)

        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client, alternates, conference, paper_reviewer_data, assignment_edges)
