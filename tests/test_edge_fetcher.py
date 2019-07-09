from matcher.EdgeFetcher import EdgeFetcher
import openreview
from helpers.Params import Params
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges
import numpy as np

class TestEdgeFetcher:

    def setup_class (cls):
        cls.counter = 0

    def setup (self):
        pass

    def create_edge (self, inv, head, fields):
        return openreview.Edge(invitation=inv,head=head, tail=fields['tail'], weight=fields.get('weight'),
                               label=fields.get('label'), readers=[], writers=[], signatures=[])


    def test_iclr (self, test_util):
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
        params = Params({Params.NUM_PAPERS: num_papers,
                         Params.NUM_REVIEWERS: num_reviewers,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: num_reviews_needed_per_paper,
                         Params.REVIEWER_MAX_PAPERS: reviewer_max_papers,
                         Params.REVIEWER_MIN_PAPERS: reviewer_min_papers,
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'TPMS': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.MATRIX_SCORE,
                                                Params.SCORE_MATRIX: score_matrix
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count(), params) #type: ConferenceConfigWithEdges
        inv = conf.conf_ids.CONF_ID + '/-/TPMS'
        print("Edge invitation is "+ inv)
        ef = EdgeFetcher(or_client)

        edge_map = ef.get_all_edges(inv)
        keys = list(edge_map.keys())
        assert 3 == len(keys)
        for k in keys:
            assert 4 == len(edge_map[k])
