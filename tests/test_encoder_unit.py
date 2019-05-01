import pytest
import time

from fields import Configuration
from Params import Params
import numpy as np
from matcher.assignment_graph.AssignmentGraph import AssignmentGraph, GraphBuilder
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges
from matcher.Encoder import Encoder
from matcher.PaperReviewerInfo import PaperReviewerInfo
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds

#Unit tests that exercise the Encoder class's two public methods: encode and decode.
class TestEncoderUnit:

    def setup_class (cls):
        cls.counter = 0

    def setup (self):
        TestEncoderUnit.counter += 1



    # @pytest.mark.skip
    def test1_encode (self, test_util):
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
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'recommendation'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, TestEncoderUnit.counter , params)
        # md = conf.get_metadata_notes_following_paper_order()
        config = conf.get_config_note()
        title = config.content[Configuration.TITLE]
        md_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids)
        md = PaperReviewerInfo(or_client, title, conf.paper_notes, conf.reviewers, md_invitations)

        now = time.time()
        enc = Encoder(md, config.content, conf.reviewers)
        print("Time to encode: ", time.time() - now)
        cost_matrix = enc._cost_matrix
        shape = cost_matrix.shape
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert(cost_matrix[r,p] == -2)

    # @pytest.mark.skip()
    def test2_encode_constraints_locks_and_vetos (self, test_util):
        '''
        lock paper 0: reviewer 0, paper 1: reviewer 1
        veto paper 0: reviewer 1, paper 2: reviewer 0
        :param test_util:
        :return:
        '''
        num_papers = 4
        num_reviewers = 3
        params = Params({Params.NUM_PAPERS: 4,
                         Params.NUM_REVIEWERS: 3,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.CONSTRAINTS_CONFIG: {Params.CONSTRAINTS_LOCKS: {0: [0], 1:[1]},
                                                     Params.CONSTRAINTS_VETOS: {0: [1], 2: [0]}},
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'recommendation'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, TestEncoderUnit.counter , params)
        # md = conf.get_metadata_notes_following_paper_order()
        config = conf.get_config_note()
        title = config.content[Configuration.TITLE]
        md_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids,
                                                        conf.conf_ids.CONFLICTS_INV_ID,
                                                        conf.conf_ids.CONSTRAINTS_INV_ID,
                                                        conf.conf_ids.CUSTOM_LOAD_INV_ID)
        md = PaperReviewerInfo(or_client, title, conf.paper_notes, conf.reviewers, md_invitations)

        now = time.time()
        enc = Encoder(md, config.content, conf.reviewers)
        print("Time to encode: ", time.time() - now)
        constraint_matrix = enc._constraint_matrix
        shape = constraint_matrix.shape
        assert shape == (num_reviewers,num_papers)
        # locks
        assert constraint_matrix[0,0] == 1
        assert constraint_matrix[1,1] == 1
        # vetos
        assert constraint_matrix[1,0] == -1
        assert constraint_matrix[0,2] == -1
        # default
        assert constraint_matrix[0,1] == 0
        assert constraint_matrix[0,3] == 0
        assert constraint_matrix[1,2] == 0
        assert constraint_matrix[1,3] == 0
        assert constraint_matrix[2,0] == 0
        assert constraint_matrix[2,1] == 0
        assert constraint_matrix[2,2] == 0
        assert constraint_matrix[2,3] == 0

    # @pytest.mark.skip()
    def test3_encode_conflicts (self, test_util):
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
        conf = ConferenceConfigWithEdges(or_client, TestEncoderUnit.counter , params)
        # md = conf.get_metadata_notes_following_paper_order()
        config = conf.get_config_note()
        title = config.content[Configuration.TITLE]
        md_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids,
                                                        conf.conf_ids.CONFLICTS_INV_ID,
                                                        conf.conf_ids.CONSTRAINTS_INV_ID,
                                                        conf.conf_ids.CUSTOM_LOAD_INV_ID)
        md = PaperReviewerInfo(or_client, title, conf.paper_notes, conf.reviewers, md_invitations)

        now = time.time()
        enc = Encoder(md, config.content, conf.reviewers)
        print("Time to encode: ", time.time() - now)
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
        # assert constraint_matrix[2,1] == 0
        assert constraint_matrix[2,2] == 0
        assert constraint_matrix[2,3] == 0

    def test4_encode_conflicts_and_constraints (self, test_util):
        '''
        conflicts paper-0/user-0, paper-1/user-2
        vetos: paper-3/users 1,2
        locks: paper-0/user-0, paper-2/user-2

        the lock of paper-0/user-0 will dominate the conflict between these two.
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
                         Params.CONSTRAINTS_CONFIG: {Params.CONSTRAINTS_VETOS: {3:[1,2]},
                                                     Params.CONSTRAINTS_LOCKS: {0: [0], 2:[2]}

                         },
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'recommendation'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, TestEncoderUnit.counter , params)
        # md = conf.get_metadata_notes_following_paper_order()
        config = conf.get_config_note()
        title = config.content[Configuration.TITLE]
        md_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids,
                                                        conf.conf_ids.CONFLICTS_INV_ID,
                                                        conf.conf_ids.CONSTRAINTS_INV_ID,
                                                        conf.conf_ids.CUSTOM_LOAD_INV_ID)
        md = PaperReviewerInfo(or_client, title, conf.paper_notes, conf.reviewers, md_invitations)

        now = time.time()
        enc = Encoder(md, config.content, conf.reviewers)
        print("Time to encode: ", time.time() - now)
        constraint_matrix = enc._constraint_matrix
        shape = constraint_matrix.shape
        assert shape == (num_reviewers,num_papers)
        # conflicts paper-0/user-0, paper-1/user-2
        #         vetos: paper-3/users 1,2
        #         locks: paper-0/user-0, paper-2/user-2
        #
        #         the lock of paper-0/user-0 will dominate the conflict between these two.
        assert constraint_matrix[0,0] == 1
        assert constraint_matrix[1,3] == -1
        assert constraint_matrix[2,1] == -1
        assert constraint_matrix[2,2] == 1
        assert constraint_matrix[2,3] == -1

        # default
        assert constraint_matrix[0,2] == 0
        assert constraint_matrix[0,1] == 0
        assert constraint_matrix[0,3] == 0
        assert constraint_matrix[1,2] == 0
        assert constraint_matrix[1,0] == 0
        assert constraint_matrix[1,1] == 0
        assert constraint_matrix[2,0] == 0



    @pytest.mark.skip
    def test_big_encode (self, test_util):
        '''
        Build a conference using edges for the three scores tpms, recommendation, bid
        :param test_util:
        :return:
        '''
        num_papers = 500
        num_reviewers = 200
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 2,
                         Params.REVIEWER_MAX_PAPERS: 6,
                         Params.SCORES_CONFIG: {Params.SCORE_NAMES_LIST: ['affinity', 'bid'],
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        now = time.time()
        conf = ConferenceConfigWithEdges(or_client, TestEncoderUnit.counter , params)
        print("Time to build test conference: ", time.time() - now)
        config = conf.get_config_note()
        title = config.content[Configuration.TITLE]
        now = time.time()
        md_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids)
        md = PaperReviewerInfo(or_client, title, conf.paper_notes, conf.reviewers, md_invitations)
        print("Time to build metadata edges: ", time.time() - now)
        now = time.time()
        enc = Encoder(md, config.content, conf.reviewers)
        print("Time to encode: ", time.time() - now)
        cost_matrix = enc._cost_matrix
        shape = cost_matrix.shape
        num_scores = len(params.scores_config[Params.SCORE_NAMES_LIST])
        assert shape == (num_reviewers,num_papers)
        for r in range(num_reviewers):
            for p in range(num_papers):
                assert(cost_matrix[r,p] == -1*num_scores)


    # @pytest.mark.skip
    def test_decode (self, test_util):
        '''
        There is a dependency where testing decode means that the Encoder must have first been instantiated and encode called.
        decode makes reference to dictionaries built during encode so I can't just remove the call to encode that is in the constructor
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
        conf = ConferenceConfigWithEdges(or_client, TestEncoderUnit.counter , params)
        papers = conf.get_paper_notes()
        reviewers = conf.reviewers
        config = conf.get_config_note()
        title = config.content[Configuration.TITLE]
        md_invitations = PaperReviewerEdgeInvitationIds(conf.score_invitation_ids)
        md = PaperReviewerInfo(or_client, title, conf.paper_notes, conf.reviewers, md_invitations)

        enc = Encoder(md, config.content, reviewers)
        cost_matrix = enc._cost_matrix
        constraint_matrix = np.zeros(np.shape(cost_matrix))
        graph_builder = GraphBuilder.get_builder('SimpleGraphBuilder')
        solver = AssignmentGraph([1] * num_reviewers, [reviewer_max_papers] * num_reviewers, [1,1,2], cost_matrix, constraint_matrix, graph_builder)
        solution = solver.solve()
        now = time.time()
        assignments_by_forum = enc.decode(solution)
        print("Time to decode: ", time.time() - now)
        assert assignments_by_forum[papers[0].id][0]['userId'] == reviewers[0]
        assert assignments_by_forum[papers[1].id][0]['userId'] == reviewers[1]
        assert assignments_by_forum[papers[2].id][0]['userId'] == reviewers[2]
        assert assignments_by_forum[papers[2].id][1]['userId'] == reviewers[3]

