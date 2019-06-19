import pytest

import logging

from helpers.Params import Params
from matcher.PaperReviewerData import PaperReviewerData
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges


class MockPaperReviewerData(PaperReviewerData):
    # override superclass with a noop so its easy to instantiate and test.
    def __init__ (self, paper_notes=None, reviewers=None, edge_invitations=None, score_spec = {},
                  inv_to_edge_map={}, conflict_edges=[], logger=logging.getLogger(__name__)):
        self._paper_notes = paper_notes
        self._reviewers = reviewers
        self.edge_invitations = edge_invitations
        self._score_specification =  score_spec
        self._inv_to_edge_map = inv_to_edge_map # not an override of superclass property - used to help mocking of edge lookup from API
        self._conflict_edges = conflict_edges # helps mocking so I don't have to call API to get these.
        self.logger = logger

    # Mocking the lookup of edges given an edge-invitation id.  This is done by passing in a map to the constructor
    # which maps each invitation id to a list of edges so we can just get the list from the map.
    def _get_all_score_edges (self, or_client, inv_id):
        return self._inv_to_edge_map[inv_id]

    def _get_all_conflict_edges (self, or_client, inv_id):
        return self._conflict_edges


class MockEdge:
    def __init__ (self, head, tail, label, weight):
        self.head = head
        self.tail = tail
        self.label = label
        self.weight = weight



class TestScoreTranslationORAPI:
    ''' Unit test makes sure a translate function can call into the openreview api'''

    @classmethod
    def setup_class(cls):
        cls.silent = True


    or_function =  """
lambda edge: 
    paper_note = or_client.get_note(id=edge.head)
    reviewer = edge.tail
    title = paper_note.content['title']
    print('The paper title is ' + title)
    return 1
"""

    # This test requires running the openreview clean-start-app because it uses a translate function that
    # calls the openreview-py API
    def test_function_calling_openreview (self, test_util):
        '''
        make sure translate function can call openreview API which means passing it a real edge so that the translate function
        can do some real work
        :return:
        '''
        num_papers = 4
        num_reviewers = 3
        params = Params({Params.NUM_PAPERS: 4,
                         Params.NUM_REVIEWERS: 3,
                         Params.NUM_REVIEWS_NEEDED_PER_PAPER: 1,
                         Params.REVIEWER_MAX_PAPERS: 2,
                         Params.SCORES_CONFIG: {Params.SCORES_SPEC: {'affinity': {'weight': 1, 'default': 0}},
                                                Params.SCORE_TYPE: Params.FIXED_SCORE,
                                                Params.FIXED_SCORE_VALUE: 0.01
                                                }
                         })

        or_client = test_util.client
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count() , params)
        papers = conf.get_paper_notes()
        pap0 = papers[0]
        reviewers = conf.reviewers
        rev0 = reviewers[0]
        edges = conf.get_score_edges(pap0,rev0)
        e0 = edges[0]
        prd = MockPaperReviewerData()
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': self.or_function}
        ws = prd._translate_edge_to_score(score_spec, e0, or_client)
        assert ws == pytest.approx(1)