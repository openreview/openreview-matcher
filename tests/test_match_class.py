import numpy as np
from matcher.match import Match
from matcher.encoder2 import Encoder2
from matcher.encoder import Encoder
from matcher.fields import Configuration
from params import Params


# Note Well:  To run this test you must be running OR with a clean db.  See README for details.

class TestMatchClass():

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

    def check_aggregate_score_edges (self, client, reviewers, papers, conference, encoder):
        agg_score_inv_id = conference.conf_ids.AGGREGATE_SCORE_ID
        for rix, r in enumerate(reviewers):
            for pix, p in enumerate(papers):
                score_edges = conference.get_score_edges(p, r)
                entry = self.make_entry_from_edges(score_edges)
                agg_score = encoder.cost_function.aggregate_score(entry, encoder.weights)
                print("reviewer",rix,"paper",pix,"agg-score",agg_score)
                ag_sc_edge = client.get_edges(invitation=agg_score_inv_id, head=p.id, tail=r)[0]
                assert ag_sc_edge.weight == agg_score

    # @pytest.mark.skip
    def test1_10papers_7reviewers (self, test_util):
        '''
        Tests 10 papers each requiring 2 reviews.  7 users each capable of giving 3 reviews.
        Expects:  produce an assignment
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
        enc = Encoder2(config=test_util.get_conference().get_config_note().content)
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,enc)


    # @pytest.mark.skip
    def test3_papers_4reviewers (self, test_util):
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
        enc = Encoder2(config=test_util.get_conference().get_config_note().content)
        self.check_aggregate_score_edges(test_util.client,reviewers,papers,conference,enc)

