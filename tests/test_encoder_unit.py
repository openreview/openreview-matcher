import pytest
import time
import numpy as np

from matcher.fields import Configuration
from helpers.Params import Params
from matcher.assignment_graph.AssignmentGraph import AssignmentGraph, GraphBuilder
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges
from matcher.Encoder import Encoder
from matcher.PaperReviewerData import PaperReviewerData
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
import matcher.cost_function

#Unit tests that exercise the Encoder class's two public methods: encode and decode.
# Each test builds a conference and then directly calls the Encoder classes methods.   Assertions are then made about the
# constraint and cost matrices within the encoder.
class TestEncoderUnit:

    def setup_class (cls):
        cls.counter = 0

    def setup (self):
        pass

    bid_translate_fn = """
lambda edge:
    if edge.label == 'low':
        return 0.2
    elif edge.label == 'medium':
        return 0.5
    elif edge.label == 'high':
        return 0.8
    elif edge.label == 'very high':
        return 0.95
    elif edge.label == 'none':
        return 0
    else:
        return 0.6
"""
    bid_translate_map = {
        'low': 0.2,
        'medium': 0.5,
        'high': 0.8,
        'very high': 0.9,
    }


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
                         Params.SCORES_CONFIG: {
                                                Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0},
                                                                     'recommendation': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                },
                         Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_MAP: {0: 0, 1: 2}},
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count() , params)
        config = conf.get_config_note()
        scores_spec = config.content[Configuration.SCORES_SPECIFICATION]
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids, conf.conf_ids.CONFLICTS_INV_ID, conf.conf_ids.CUSTOM_LOAD_INV_ID)
        pr_data = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations, scores_spec)

        enc = Encoder(pr_data)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert(cost_matrix[r,p] == -2)

    # @pytest.mark.skip
    def test_encode_with_bid_translation (self, test_util):
        '''
        Build a conference using edges for the two scores.
        N.B.  The 0.01 fixed score sets all scores to 0.01 which results in a weighted sum (aggregate) score of 0.02 (weights are 1)
        The 0.02 is then converted into a cost of -2 by the Encoder.
        :param test_util:
        :return:
        '''
        num_papers = 3
        num_reviewers = 4

        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.SCORES_CONFIG: {
                             Params.SCORES_SPEC: {'bid': {'weight': 1, 'default': 0, 'translate_fn': self.bid_translate_fn}},
                             Params.SCORE_TYPE: Params.FIXED_SCORE,
                             Params.FIXED_SCORE_VALUE: 'high'
                         },
                         Params.CUSTOM_LOAD_CONFIG: {Params.CUSTOM_LOAD_MAP: {0: 0, 1: 2}},
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count() , params)
        config = conf.get_config_note()
        scores_spec = config.content[Configuration.SCORES_SPECIFICATION]
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids, conf.conf_ids.CONFLICTS_INV_ID, conf.conf_ids.CUSTOM_LOAD_INV_ID)
        pr_data = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations, scores_spec)

        enc = Encoder(pr_data)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        # all scores are set at bid:'high' which translates to 0.8 and then to a cost of -80
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert(cost_matrix[r,p] == -80)

    # @pytest.mark.skip
    def test_mixed_score_types (self, test_util):
        '''
        Uses two score types; Bids are translated via the function.  Also tests when scores are not given by an edge to verify that it uses the
        default values.
        :param test_util:
        :return:
        '''
        num_papers = 4
        num_reviewers = 4
        aff_matrix = np.array([
            [10, 0, 0, 0],
            [0, 10, 0, 0],
            [0, 0, 10, 0],
            [0, 0, 0, 0]
        ])
        bid_matrix = np.array([
            ['very high', 'low', 'low', 'low'],
            ['low', 'very high', 'low', 'low'],
            ['low', 'low', 'very high', 'low'],
            [0, 0, 0, 0]
        ])
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.SCORES_CONFIG: {
                             Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0},
                                                  'bid': {'weight': 1, 'default': 0, 'translate_fn': self.bid_translate_fn}},
                             Params.SCORE_TYPE: Params.MATRIX_SCORE,
                             Params.OMIT_ZERO_SCORE_EDGES: True,
                             Params.SCORE_MATRIX: {'affinity': aff_matrix, 'bid': bid_matrix}
                         }})

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count() , params)
        config = conf.get_config_note()
        scores_spec = config.content[Configuration.SCORES_SPECIFICATION]
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids, conf.conf_ids.CONFLICTS_INV_ID, conf.conf_ids.CUSTOM_LOAD_INV_ID)
        pr_data = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations, scores_spec)

        enc = Encoder(pr_data)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        assert cost_matrix[0,0] == -1095
        assert cost_matrix[1,1] == -1095
        assert cost_matrix[2,2] == -1095
        assert cost_matrix[0,1] == -20
        assert cost_matrix[0,2] == -20
        assert cost_matrix[0,3] == -20
        assert cost_matrix[1,0] == -20
        assert cost_matrix[1,2] == -20
        assert cost_matrix[1,3] == -20
        assert cost_matrix[2,0] == -20
        assert cost_matrix[2,1] == -20
        assert cost_matrix[2,3] == -20
        assert cost_matrix[3,0] == 0
        assert cost_matrix[3,1] == 0
        assert cost_matrix[3,2] == 0
        assert cost_matrix[3,3] == 0

    def test_encoder_weighting (self, test_util):
        '''
        Makes sure that weight is correctly applied as part of the process of computing the score during encoding.
        :param test_util:
        :return:
        '''
        num_papers = 4
        num_reviewers = 4
        aff_matrix = np.array([
            [10, 0, 0, 0],
            [0, 10, 0, 0],
            [0, 0, 10, 0],
            [0, 0, 0, 0]
        ])
        bid_matrix = np.array([
            ['very high', 'low', 'low', 'low'],
            ['low', 'very high', 'low', 'low'],
            ['low', 'low', 'very high', 'low'],
            [0, 0, 0, 0]
        ])
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.SCORES_CONFIG: {
                             Params.SCORES_SPEC: {'affinity': {'weight': 10, 'default': 0},
                                                  'bid': {'weight': 2, 'default': 0, 'translate_map': self.bid_translate_map}},
                             Params.SCORE_TYPE: Params.MATRIX_SCORE,
                             Params.OMIT_ZERO_SCORE_EDGES: True,
                             Params.SCORE_MATRIX: {'affinity': aff_matrix, 'bid': bid_matrix}
                         }})

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count() , params)
        config = conf.get_config_note()
        scores_spec = config.content[Configuration.SCORES_SPECIFICATION]
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids, conf.conf_ids.CONFLICTS_INV_ID, conf.conf_ids.CUSTOM_LOAD_INV_ID)
        pr_data = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations, scores_spec)

        enc = Encoder(pr_data)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        # scores with [10*10 + 0.9 * 2] * 100 = 101.8 * 100 = 10180.
        assert cost_matrix[0,0] == -10180
        assert cost_matrix[1,1] == -10180
        assert cost_matrix[2,2] == -10180
        # scores with [10*0 + 0.2 * 2] * 100 = -4
        assert cost_matrix[0,1] == -40
        assert cost_matrix[0,2] == -40
        assert cost_matrix[0,3] == -40
        assert cost_matrix[1,0] == -40
        assert cost_matrix[1,2] == -40
        assert cost_matrix[1,3] == -40
        assert cost_matrix[2,0] == -40
        assert cost_matrix[2,1] == -40
        assert cost_matrix[2,3] == -40
        # scores with [0*10 + 0*2] * 100 = 0
        assert cost_matrix[3,0] == 0
        assert cost_matrix[3,1] == 0
        assert cost_matrix[3,2] == 0
        assert cost_matrix[3,3] == 0



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
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0},
                                                                     'recommendation': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count(), params)
        config = conf.get_config_note()
        scores_spec = config.content[Configuration.SCORES_SPECIFICATION]
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids,
                                                        conf.conf_ids.CONFLICTS_INV_ID,
                                                        conf.conf_ids.CUSTOM_LOAD_INV_ID)
        prd = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations, scores_spec)

        enc = Encoder(prd)
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
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0},
                                                                     'recommendation': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: fixed_score
                                                }
                         })
        ag_cost = 0
        for spec in params.scores_config[Params.SCORES_SPEC].values():
            ag_cost += spec['weight'] * fixed_score
        correct_cost = matcher.cost_function.aggregate_score_to_cost(ag_cost)
        or_client = test_util.client
        now = time.time()
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count(), params)
        print("Time to build test conference: ", time.time() - now)
        config = conf.get_config_note()
        scores_spec = config.content[Configuration.SCORES_SPECIFICATION]
        now = time.time()
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids,
                                                          conf.conf_ids.CONFLICTS_INV_ID,
                                                          conf.conf_ids.CUSTOM_LOAD_INV_ID)
        prd = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations, scores_spec)
        print("Time to build metadata edges: ", time.time() - now)
        now = time.time()
        enc = Encoder(prd)
        print("Time to encode: ", time.time() - now)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert cost_matrix[r,p] == correct_cost


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
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
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
        scores_spec = config.content[Configuration.SCORES_SPECIFICATION]
        edge_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids,
                                                          conf.conf_ids.CONFLICTS_INV_ID,
                                                          conf.conf_ids.CUSTOM_LOAD_INV_ID)
        prd = PaperReviewerData(or_client, conf.paper_notes, conf.reviewers, edge_invitations, scores_spec)

        enc = Encoder(prd)
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

