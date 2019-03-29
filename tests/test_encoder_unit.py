import pytest
import time
from params import Params
import numpy as np
from matcher.assignment_graph.AssignmentGraph import AssignmentGraph, GraphBuilder
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges
from helpers.conference_config import ConferenceConfig
from matcher.encoder import Encoder
from matcher.Metadata import Metadata

class TestEncoderUnit:

    def setup_class (cls):
        cls.counter = 0

    def setup (self):
        TestEncoderUnit.counter += 1



    # @pytest.mark.skip
    def test_encode (self, test_util):
        '''
        Build a conference using edges for the three scores tpms, recommendation, bid
        :param test_util:
        :return:
        '''
        num_papers = 4
        num_reviewers = 3
        params = Params({Params.NUM_PAPERS: 4,
                         Params.NUM_REVIEWERS: 3,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfig(or_client, TestEncoderUnit.counter , params)
        md = conf.get_metadata_notes_following_paper_order()
        config = conf.get_config_note()
        now = time.time()
        enc = Encoder(md, config.content, conf.reviewers)
        print("Time to encode: ", time.time() - now)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert(cost_matrix[r,p] == -1)

    @pytest.mark.skip
    def test_big_encode (self, test_util):
        '''
        Build a conference using edges for the three scores tpms, recommendation, bid
        :param test_util:
        :return:
        '''
        num_papers = 2000
        num_reviewers = 1500
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                         Params.REVIEWER_MAX_PAPERS: 3,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        now = time.time()
        conf = ConferenceConfig(or_client, TestEncoderUnit.counter , params)
        print("Time to build test conference: ", time.time() - now)
        md = conf.get_metadata_notes_following_paper_order()
        config = conf.get_config_note()
        now = time.time()
        enc = Encoder(md, config.content, conf.reviewers)
        print("Time to encode: ", time.time() - now)
        cost_matrix = enc.cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert(cost_matrix[r,p] == -1)

    # @pytest.mark.skip
    def test_decode (self, test_util):
        '''
        There is a dependency where testing decode means that the Encoder must have first been instantiated and this
        calls the encode method.  Unforunately, decode makes reference to dictionaries built during encode so I can't
        just remove the call to encode that is in the constructor
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
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_needed_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity'],
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })
        '''
        Test that the decoder produces the expected assignment.   Its necessary to configure
        the inputs to get a predictable solution.   We send a score matrix that forces
        it to choose the expected solution reviewer-0->paper-0, 1->1, 2->2, 3->2
                         
        '''
        or_client = test_util.client
        conf = ConferenceConfig(or_client, TestEncoderUnit.counter , params)
        papers = conf.get_paper_notes()
        reviewers = conf.reviewers
        md = conf.get_metadata_notes_following_paper_order()
        config = conf.get_config_note()
        enc = Encoder(md, config.content, reviewers)
        cost_matrix = enc.cost_matrix
        constraint_matrix = np.zeros(np.shape(cost_matrix))
        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        solver = AssignmentGraph([1] * num_reviewers, [reviewer_max_papers] * num_reviewers, [1,1,2], cost_matrix, constraint_matrix, graph_builder)
        solution = solver.solve()
        now = time.time()
        assignments_by_forum, alternates_by_forum = enc.decode(solution)
        print("Time to decode: ", time.time() - now)
        assert assignments_by_forum[papers[0].id][0]['userId'] == reviewers[0]
        assert assignments_by_forum[papers[1].id][0]['userId'] == reviewers[1]
        assert assignments_by_forum[papers[2].id][0]['userId'] == reviewers[2]
        assert assignments_by_forum[papers[2].id][1]['userId'] == reviewers[3]

