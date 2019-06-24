import pytest
from helpers.Params import Params
from matcher.PaperReviewerData import PaperReviewerData
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
from matcher.EdgeFetcher import EdgeFetcher
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges
from openreview import Edge

class MockEdgeFetcher(EdgeFetcher):
    def __init__ (self, inv_to_edge_map):
        self.inv_to_edge_map = inv_to_edge_map

    def get_all_edges (self,  inv_id):
        return self.inv_to_edge_map[inv_id]



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
        prd = PaperReviewerData(or_client,[],[],PaperReviewerEdgeInvitationIds([]),{},None)
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': self.or_function}
        ws = prd._translate_edge_to_score(score_spec, e0, or_client)
        assert ws == pytest.approx(1)