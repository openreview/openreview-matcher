import pytest
import time
import numpy as np

from matcher.WeightedScorer import WeightedScorer
from matcher.fields import Configuration
from helpers.Params import Params
from matcher.assignment_graph.AssignmentGraph import AssignmentGraph, GraphBuilder
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges
from matcher.Encoder import Encoder
from matcher.PaperReviewerData import PaperReviewerData
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds

#Unit tests that exercise the Encoder class's two public methods: encode and decode.
# Each test builds a conference and then directly calls the Encoder classes methods.   Assertions are then made about the
# constraint and cost matrices within the encoder.
class TestEncoderUnit:

    def setup_class (cls):
        cls.counter = 0

    def setup (self):
        pass



    # @pytest.mark.skip
    def test_simple_encode (self, test_util):
        '''
        Build a conference using edges for the two scores.
        N.B.  The 0.01 fixed score sets all scores to 0.01 which results in a weighted sum (aggregate) score of 0.02 (weights are 1)
        The 0.02 is then converted into a cost of -2 by the Encoder.
        :param test_util:
        :return:
        '''
        num_papers = 4
        num_reviewers = 3
        params = Params({Params.NUM_PAPERS: 4,
                         Params.NUM_REVIEWERS: 3,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'recommendation'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count() , params)
        config = conf.get_config_note()
        md_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids)
        pr_data = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, md_invitations)

        enc = Encoder(pr_data, config.content)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert(cost_matrix[r,p] == -2)


    # @pytest.mark.skip()
    def test_encode_conflicts (self, test_util):
        '''
        conflicts paper-0/user-0, paper-1/user-2
        :param test_util:
        :return:
        '''
        num_papers = 4
        num_reviewers = 3
        params = Params({Params.NUM_PAPERS: 4,
                         Params.NUM_REVIEWERS: 3,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.CONFLICTS_CONFIG: {0: [0], 1:[2]},
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'recommendation'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count(), params)
        config = conf.get_config_note()
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids,
                                                        conf.conf_ids.CONFLICTS_INV_ID,
                                                        conf.conf_ids.CUSTOM_LOAD_INV_ID)
        prd = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations)

        enc = Encoder(prd, config.content)
        constraint_matrix = enc._constraint_matrix
        shape = constraint_matrix.shape
        assert shape == (num_reviewers,num_papers)
        # conflicts paper-0/user-0, paper-1/user-2
        assert constraint_matrix[0,0] == -1
        assert constraint_matrix[2,1] == -1
        # default
        assert constraint_matrix[1,0] == 0
        assert constraint_matrix[0,2] == 0
        assert constraint_matrix[0,1] == 0
        assert constraint_matrix[0,3] == 0
        assert constraint_matrix[1,2] == 0
        assert constraint_matrix[1,3] == 0
        assert constraint_matrix[2,0] == 0
        assert constraint_matrix[2,2] == 0
        assert constraint_matrix[2,3] == 0




    @pytest.mark.skip
    def test_big_encode (self, test_util):
        '''
        Build a conference using edges for the three scores tpms, recommendation, bid
        N.B.  The 0.01 fixed score sets all scores to 0.01 which results in a weighted sum (aggregate) score of 0.02 (weights are 1)
        The 0.02 is then converted into a cost of -2 by the Encoder.
        :param test_util:
        :return:
        '''
        num_papers = 500
        num_reviewers = 200
        fixed_score = 0.01
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                         Params.REVIEWER_MAX_PAPERS: 6,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'bid'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: fixed_score
                                                }
                         })

        or_client = test_util.client
        now = time.time()
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count(), params)
        print("Time to build test conference: ", time.time() - now)
        config = conf.get_config_note()
        now = time.time()
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids)
        prd = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations)
        print("Time to build metadata edges: ", time.time() - now)
        now = time.time()
        enc = Encoder(prd, config.content)
        print("Time to encode: ", time.time() - now)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        agg_score = WeightedScorer().weighted_score({sc_name: fixed_score for sc_name in params.scores_config[Params.SCORE_NAMES_LIST]})
        correct_score = enc._cost_fn(agg_score)
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert cost_matrix[r,p] == correct_score


    # @pytest.mark.skip
    def test_decode (self, test_util):
        '''
        Test that the decode returns a correct assignment dictionary.
        Must manually call the encoder.encode and solver.
        We send a score matrix that forces
        it to choose the expected solution reviewer-0->paper-0, 1->1, 2->2, 3->2
        '''
        score_matrix = np.array([
            [10, 0, 0],
            [0, 10, 0],
            [0, 0, 10],
            [0, 0, 10]
        ])
        num_papers = 3
        num_reviewers = 4
        num_reviews_needed_per_paper = 2
        reviewer_max_papers = 2
        reviewer_min_papers = 1
        paper_demands = [1, 1, 2]
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_needed_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.REVIEWER_MIN_PAPERS: reviewer_min_papers,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })
        '''
        Test that the decoder produces the expected assignment.   Its necessary to configure
        the inputs to get a predictable solution.   
                         
        '''
        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count(), params)
        papers = conf.get_paper_notes()
        reviewers = conf.reviewers
        config = conf.get_config_note()
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids)
        prd = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations)

        enc = Encoder(prd, config.content)
        cost_matrix = enc.cost_matrix
        constraint_matrix = np.zeros(np.shape(cost_matrix))
        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        solver = AssignmentGraph([reviewer_min_papers] * num_reviewers, [reviewer_max_papers] * num_reviewers,
                                 paper_demands, cost_matrix, constraint_matrix, graph_builder)
        solution = solver.solve()
        assignments_by_forum = enc.decode(solution)
        assert assignments_by_forum[papers[0].id][0].user == reviewers[0]
        assert assignments_by_forum[papers[1].id][0].user == reviewers[1]
        assert assignments_by_forum[papers[2].id][0].user == reviewers[2]
        assert assignments_by_forum[papers[2].id][1].user == reviewers[3]

