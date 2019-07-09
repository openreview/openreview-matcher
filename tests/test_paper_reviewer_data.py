import pytest
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
from matcher.PaperReviewerData import PaperReviewerData
from matcher.EdgeFetcher import EdgeFetcher
from openreview import Edge, Note

from matcher.PaperUserScores import PaperUserScores

class MockEdgeFetcher(EdgeFetcher):
    def __init__ (self, inv_to_edge_map):
        self.inv_to_edge_map = inv_to_edge_map

    def get_all_edges (self,  inv_id):
        return self.inv_to_edge_map[inv_id]


def cr_edge (head, tail, label, weight):
    e = Edge(head,tail,None,[],[],[],label=label, weight=weight)
    return e

def cr_paper (id):
    n = Note(None,[],[],[],{},id=id)
    return n

class TestPaperReviewerData:
    '''Tests the PaperReviewerData._load_score_map method'''

    @classmethod
    def setup_class(cls):
        cls.silent = True

    bid_translate_map = {
        'low': 0.2,
        'medium': 0.5,
        'high': 0.8,
        'very high': 0.9,
    }


    bid_translate_map2 = {
        'low': 0.2,
        'medium': 0.5,
        'high': 0.8,
        'very high': 0.93,
    }


    # requires that openreview be running because it needs an openreview client
    def test_base_case (self):
        pd = PaperReviewerData([],[],PaperReviewerEdgeInvitationIds([]),{},None)
        assert pd != None


    def test_some_numeric_edges_given (self):
        '''
        For 2 papers and 2 reviewers set up score edges that are numeric,  Paper1->Reviewer0 has no score edges and will
        get its scores from defaults.
        :return:
        '''

        score_spec = {'conf/affinity': {'weight': 1, 'default': 0.35},
                      'conf/recommendation': {'weight': 2, 'default': 0.66},
                      'conf/xscore': {'weight': 3, 'default': 0}
                      }
        score_edge_invitation_ids = score_spec.keys()
        paper_notes = [cr_paper('PaperId0'), cr_paper('PaperId1')]
        reviewers = ['ReviewerId0', 'ReviewerId1']

        edge_invitations = PaperReviewerEdgeInvitationIds(score_edge_invitation_ids)
        ae0 = cr_edge(paper_notes[0].id,reviewers[0],label='affinity', weight=0.2)
        re0 = cr_edge(paper_notes[0].id,reviewers[0],label='recommendation', weight=0.4)
        xe0 = cr_edge(paper_notes[0].id,reviewers[0],label='xscore', weight=0.6)
        ae1 = cr_edge(paper_notes[1].id,reviewers[1],label='affinity', weight=0.3)
        re1 = cr_edge(paper_notes[1].id,reviewers[1],label='recommendation', weight=0.5)
        xe1 = cr_edge(paper_notes[1].id,reviewers[1],label='xscore', weight=0.7)
        ae2 = cr_edge(paper_notes[0].id,reviewers[1],label='affinity', weight=0.75)
        re2 = cr_edge(paper_notes[0].id,reviewers[1],label='recommendation', weight=0.85)
        xe2 = cr_edge(paper_notes[0].id,reviewers[1],label='xscore', weight=0.95)
        inv_to_edge_map = {'conf/affinity': {paper_notes[0].id: [ae0, ae2],
                                             paper_notes[1].id: [ae1]},
                           'conf/recommendation': {paper_notes[0].id: [re0, re2],
                                                   paper_notes[1].id: [re1]},
                           'conf/xscore': {paper_notes[0].id: [xe0, xe2],
                                           paper_notes[1].id: [xe1]}
                           }

        edge_fetcher = MockEdgeFetcher(inv_to_edge_map=inv_to_edge_map)
        prd = PaperReviewerData(paper_notes, reviewers, edge_invitations=edge_invitations, score_specification=score_spec,
                                edge_fetcher=edge_fetcher)
        prd._load_score_map()


        pair = prd.get_entry('PaperId0', 'ReviewerId0') #type: PaperUserScores
        # 1 * 0.2 + 2 * 0.4 + 3 * 0.6 = 2.8
        assert pair.aggregate_score == pytest.approx(2.8)
        assert pair.conflicts == []
        pair = prd.get_entry('PaperId1', 'ReviewerId1')
        # 1 * 0.3 + 2 * 0.5 + 3 * 0.7 = 3.4
        assert pair.aggregate_score == pytest.approx(3.4)
        assert pair.conflicts == []

        pair = prd.get_entry('PaperId0', 'ReviewerId1')
        # 1 * 0.75 + 2 * 0.85 + 3 * 0.95 = 5.3
        assert pair.aggregate_score == pytest.approx(5.3)
        assert pair.conflicts == []

        # This pair is created from default info - not edges
        pair = prd.get_entry('PaperId1', 'ReviewerId0')
        # 1 * 0.35 + 2 * 0.66 + 3 * 0 = 1.67
        assert pair.aggregate_score == pytest.approx(1.67)
        assert pair.conflicts == []


    def test_some_symbolic_and_numeric_edges (self):
        '''
         For 2 papers and 2 reviewers set up score edges.  Bid edges involve translation.
           Paper1->Reviewer0 has no score edges and will get its scores from defaults.
        :return:
        '''

        score_spec = {'conf/affinity': {'weight': 1, 'default': 0.35},
                      'conf/recommendation': {'weight': 2, 'default': 0.66},
                      'conf/bid': {'weight': 3, 'default': .1, 'translate_map': self.bid_translate_map}
                      }
        score_edge_invitation_ids = score_spec.keys()
        paper_notes = [cr_paper('PaperId0'), cr_paper('PaperId1')]
        reviewers = ['ReviewerId0', 'ReviewerId1']

        edge_invitations = PaperReviewerEdgeInvitationIds(score_edge_invitation_ids)
        ae0 = cr_edge(paper_notes[0].id,reviewers[0],label='affinity', weight=0.2)
        re0 = cr_edge(paper_notes[0].id,reviewers[0],label='recommendation', weight=0.4)
        xe0 = cr_edge(paper_notes[0].id,reviewers[0],label='low', weight=0.6)
        ae1 = cr_edge(paper_notes[1].id,reviewers[1],label='affinity', weight=0.3)
        re1 = cr_edge(paper_notes[1].id,reviewers[1],label='recommendation', weight=0.5)
        xe1 = cr_edge(paper_notes[1].id,reviewers[1],label='medium', weight=0.7)
        ae2 = cr_edge(paper_notes[0].id,reviewers[1],label='affinity', weight=0.75)
        re2 = cr_edge(paper_notes[0].id,reviewers[1],label='recommendation', weight=0.85)
        xe2 = cr_edge(paper_notes[0].id,reviewers[1],label='high', weight=0.95)

        inv_to_edge_map = {'conf/affinity': {paper_notes[0].id: [ae0, ae2],
                                             paper_notes[1].id: [ae1]},
                           'conf/recommendation': {paper_notes[0].id: [re0, re2],
                                                   paper_notes[1].id: [re1]},
                           'conf/bid': {paper_notes[0].id: [xe0, xe2],
                                           paper_notes[1].id: [xe1]}
                           }

        edge_fetcher = MockEdgeFetcher(inv_to_edge_map=inv_to_edge_map)
        prd = PaperReviewerData(paper_notes, reviewers, edge_invitations=edge_invitations, score_specification=score_spec,
                                edge_fetcher=edge_fetcher)
        prd._load_score_map()


        pair = prd.get_entry('PaperId0', 'ReviewerId0') #type: PaperUserScores
        # 1 * 0.2 + 2 * 0.4 + 3 * 0.2 = 1.6
        assert pair.aggregate_score == pytest.approx(1.6)
        assert pair.conflicts == []
        pair = prd.get_entry('PaperId1', 'ReviewerId1')
        # 1 * 0.3 + 2 * 0.5 + 3 * 0.5 = 2.8
        assert pair.aggregate_score == pytest.approx(2.8)
        assert pair.conflicts == []

        pair = prd.get_entry('PaperId0', 'ReviewerId1')
        # 1 * 0.75 + 2 * 0.85 + 3 * 0.8 = 4.85
        assert pair.aggregate_score == pytest.approx(4.85)
        assert pair.conflicts == []

        # This pair is created from default info - not edges
        pair = prd.get_entry('PaperId1', 'ReviewerId0')
        # 1 * 0.35 + 2 * 0.66 + 3 * 0.1 = 1.97
        assert pair.aggregate_score == pytest.approx(1.97)
        assert pair.conflicts == []


    def test_some_symbolic_and_numeric_edges_and_conflicts (self):
        '''
         For 2 papers and 2 reviewers set up score edges.  Bid edges involve translation.
           Paper1->Reviewer0 has no score edges and will get its scores from defaults.
           Conflicts added Paper0->Reviewer0
        :return:
        '''

        score_spec = {'conf/affinity': {'weight': 1, 'default': 0.35},
                      'conf/recommendation': {'weight': 2, 'default': 0.66},
                      'conf/bid': {'weight': 3, 'default': .1, 'translate_map': self.bid_translate_map}
                      }
        score_edge_invitation_ids = score_spec.keys()
        conflict_edge_invitation_id = 'conf/Conflicts'
        paper_notes = [cr_paper('PaperId0'), cr_paper('PaperId1')]
        reviewers = ['ReviewerId0', 'ReviewerId1']

        edge_invitations = PaperReviewerEdgeInvitationIds(score_edge_invitation_ids, conflicts=conflict_edge_invitation_id)
        ae0 = cr_edge(paper_notes[0].id,reviewers[0],label='affinity', weight=0.2)
        re0 = cr_edge(paper_notes[0].id,reviewers[0],label='recommendation', weight=0.4)
        xe0 = cr_edge(paper_notes[0].id,reviewers[0],label='low', weight=0.6)
        # conflict between paper0 and reviewer 0
        conf0 = cr_edge(paper_notes[0].id,reviewers[0], label=['umass.edu', 'google.com'], weight=0)

        ae1 = cr_edge(paper_notes[1].id,reviewers[1],label='affinity', weight=0.3)
        re1 = cr_edge(paper_notes[1].id,reviewers[1],label='recommendation', weight=0.5)
        xe1 = cr_edge(paper_notes[1].id,reviewers[1],label='medium', weight=0.7)
        ae2 = cr_edge(paper_notes[0].id,reviewers[1],label='affinity', weight=0.75)
        re2 = cr_edge(paper_notes[0].id,reviewers[1],label='recommendation', weight=0.85)
        xe2 = cr_edge(paper_notes[0].id,reviewers[1],label='high', weight=0.95)
        inv_to_edge_map = {'conf/affinity': {paper_notes[0].id: [ae0, ae2],
                                             paper_notes[1].id: [ae1]},
                           'conf/recommendation': {paper_notes[0].id: [re0, re2],
                                                   paper_notes[1].id: [re1]},
                           'conf/bid': {paper_notes[0].id: [xe0, xe2],
                                        paper_notes[1].id: [xe1]},
                           conflict_edge_invitation_id: {paper_notes[0].id: [conf0]}
                           }

        edge_fetcher = MockEdgeFetcher(inv_to_edge_map=inv_to_edge_map)
        prd = PaperReviewerData(paper_notes, reviewers, edge_invitations=edge_invitations, score_specification=score_spec,
                                edge_fetcher=edge_fetcher)

        prd._load_score_map()


        pair = prd.get_entry('PaperId0', 'ReviewerId0') #type: PaperUserScores
        # 1 * 0.2 + 2 * 0.4 + 3 * 0.2 = 1.6
        assert pair.aggregate_score == pytest.approx(1.6)
        assert pair.conflicts == ['umass.edu', 'google.com']
        pair = prd.get_entry('PaperId1', 'ReviewerId1')
        # 1 * 0.3 + 2 * 0.5 + 3 * 0.5 = 2.8
        assert pair.aggregate_score == pytest.approx(2.8)
        assert pair.conflicts == []

        pair = prd.get_entry('PaperId0', 'ReviewerId1')
        # 1 * 0.75 + 2 * 0.85 + 3 * 0.8 = 4.85
        assert pair.aggregate_score == pytest.approx(4.85)
        assert pair.conflicts == []

        # This pair is created from default info - not edges
        pair = prd.get_entry('PaperId1', 'ReviewerId0')
        # 1 * 0.35 + 2 * 0.66 + 3 * 0.1 = 1.97
        assert pair.aggregate_score == pytest.approx(1.97)
        assert pair.conflicts == []




    def test_numeric (self):
        '''
        make sure numeric score on edge is returned correctly
        :return:
        '''
        prd = PaperReviewerData([],[],PaperReviewerEdgeInvitationIds([]),{},None)
        score_spec = {'weight': 1, 'default': 0.35}
        # fake edge holding a floating point weight
        e = cr_edge('PaperId','ReviewerId', None, 0.8)
        ws = prd._translate_edge_to_score(score_spec, e)
        assert ws == pytest.approx(0.8)

    def test_symbol_translate_map (self):
        '''
        make sure symbolic score on edge is translated correctly
        :return:
        '''
        prd = PaperReviewerData([],[],PaperReviewerEdgeInvitationIds([]),{},None)
        score_spec = {'weight': 3, 'default': 0, 'translate_map': self.bid_translate_map2}
        # a fake bid edge where the label is holding the symbol
        e = cr_edge('PaperId','ReviewerId','very high', None)
        ws = prd._translate_edge_to_score(score_spec, e)
        assert ws == pytest.approx(0.93)

    def test_no_return_value (self):
        '''
        make sure translate function that does not return anything fails
        :return:
        '''
        prd = PaperReviewerData([],[],PaperReviewerEdgeInvitationIds([]),{},None)
        # translate map returns None for "mystery"
        score_spec = {'weight': 3, 'default': 0, 'translate_map': self.bid_translate_map2}
        e = cr_edge('PaperId','ReviewerId','mystery', None)
        with pytest.raises(TypeError):
            ws = prd._translate_edge_to_score(score_spec, e, None)





