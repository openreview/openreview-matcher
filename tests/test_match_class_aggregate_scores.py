import numpy as np
import pytest
from exc.exceptions import NotFoundError
from matcher.Match import Match
from matcher.Encoder import Encoder
from matcher.fields import Configuration
from matcher.PaperUserScores import PaperUserScores
from helpers.Params import Params

# Unit tests that make sure that aggregate score edges are correctly produced when a match is run.
#  Each test uses the test_util fixture to build a conference.  We directly access the Matcher object
# to run the matcher.  To test, we then create an encoder object and use it to compute the aggregate score of each paper/reviewer
# and then verify that an aggregate_score edge was produced with that value.
# N.B.:  To run this test you must be running OR with a clean db.  See README for details.
class TestMatchClassAggregateScores():

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
    def check_aggregate_score_edges_old (self, client, reviewers, papers, conference, encoder):
        agg_score_inv_id = conference.conf_ids.AGGREGATE_SCORE_ID
        for rix, r in enumerate(reviewers):
            for pix, p in enumerate(papers):
                score_edges = conference.get_score_edges(p, r)
                entry = self.make_entry_from_edges(score_edges)
                agg_score = encoder.cost_function.aggregate_score(entry, encoder.weights)
                ag_sc_edge = client.get_edges(invitation=agg_score_inv_id, head=p.id, tail=r)[0]
                assert ag_sc_edge.weight == agg_score

    # verify aggregate score edges have values that are correct
    def check_aggregate_score_edges (self, client, reviewers, papers, conference, paper_reviewer_data):
        agg_score_inv_id = conference.conf_ids.AGGREGATE_SCORE_ID
        for rix, r in enumerate(reviewers):
            for pix, p in enumerate(papers):
                paper_user_scores = paper_reviewer_data.get_entry(p.id, r) #type: PaperUserScores
                agg_score = paper_user_scores.aggregate_score
                ag_sc_edge = client.get_edges(invitation=agg_score_inv_id, head=p.id, tail=r)[0]
                assert ag_sc_edge.weight == agg_score

    # @pytest.mark.skip
    def test1_10papers_7reviewers (self, test_util):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 3 reviews.
        Validates that the output aggregate score edges are correct with respect to the paper-reviewer scores input
        '''
        num_papers = 10
        num_reviewers = 7
        num_reviews_per_paper = 2
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: 3,
                         Params.SCORES_CONFIG: { Params.SCORE_TYPE: Params.INCREMENTAL_SCORE,
                                                 Params.SCORE_INCREMENT: 0.01,
                                                 Params.SCORE_NAMES_LIST: ['affinity']}
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
        # Verify for every paper P and reviewer R that there is an aggregate score edge with a weight set to
        # the matcher's cost_func applied to the score edges for P and R * the weights.
        # Its not safe to just compare the edges to the cost_matrix because that's what they were built from.  Going back to the
        # score edges will be closer to the source of the data that forms the cost.
        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        # enc = Encoder(config=test_util.get_conference().get_config_note().content)
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client, reviewers, papers, conference, paper_reviewer_data)


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

        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert len(aggregate_score_edges) == num_reviewers * num_papers

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,paper_reviewer_data)
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
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CONFLICTS_CONFIG: {0: [0]},
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
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,paper_reviewer_data)
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
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.CONFLICTS_CONFIG: {0: [0]},
                         Params.CONSTRAINTS_CONFIG: {Params.CONSTRAINTS_LOCKS: {0: [0]}},
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
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,paper_reviewer_data)
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
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
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

        aggregate_score_edges = conference.get_aggregate_score_edges()
        assert len(aggregate_score_edges) == num_reviewers * num_papers

        reviewers = conference.reviewers
        papers = conference.get_paper_notes()
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,paper_reviewer_data)
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
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'recommendation', 'bid'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.OMIT_ZERO_SCORE_EDGES: True,
                                                Params.FIXED_SCORE_VALUE: 0
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
        paper_reviewer_data = match.paper_reviewer_data
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,paper_reviewer_data)
