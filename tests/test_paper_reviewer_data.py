import pytest

import logging

from PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
from matcher.PaperReviewerData import PaperReviewerData

from matcher.PaperUserScores import PaperUserScores

# Create a mock PaperReviewerData class which inherits the method (.load_score_map) that is tested by the unit tests.
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

class MockPaperNote:
    def __init__ (self, id):
        self.id = id


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
        paper_notes = [MockPaperNote('PaperId0'), MockPaperNote('PaperId1')]
        reviewers = ['ReviewerId0', 'ReviewerId1']

        edge_invitations = PaperReviewerEdgeInvitationIds(score_edge_invitation_ids)
        ae0 = MockEdge(paper_notes[0].id,reviewers[0],label='affinity', weight=0.2)
        re0 = MockEdge(paper_notes[0].id,reviewers[0],label='recommendation', weight=0.4)
        xe0 = MockEdge(paper_notes[0].id,reviewers[0],label='xscore', weight=0.6)
        ae1 = MockEdge(paper_notes[1].id,reviewers[1],label='affinity', weight=0.3)
        re1 = MockEdge(paper_notes[1].id,reviewers[1],label='recommendation', weight=0.5)
        xe1 = MockEdge(paper_notes[1].id,reviewers[1],label='xscore', weight=0.7)
        ae2 = MockEdge(paper_notes[0].id,reviewers[1],label='affinity', weight=0.75)
        re2 = MockEdge(paper_notes[0].id,reviewers[1],label='recommendation', weight=0.85)
        xe2 = MockEdge(paper_notes[0].id,reviewers[1],label='xscore', weight=0.95)
        inv_to_edge_map = {'conf/affinity': [ae0, ae1, ae2],
                           'conf/recommendation': [re0, re1, re2],
                           'conf/xscore': [xe0, xe1, xe2]}
        prd = MockPaperReviewerData(paper_notes, reviewers, edge_invitations=edge_invitations, score_spec=score_spec, inv_to_edge_map=inv_to_edge_map, conflict_edges=[])
        prd._load_score_map(None)


        pair: PaperUserScores = prd.get_entry('PaperId0', 'ReviewerId0')
        # 1 * 0.2 + 2 * 0.4 + 3 * 0.6 = 2.8
        assert pair.aggregate_score == pytest.approx(2.8)
        assert pair.conflicts == []
        pair: PaperUserScores = prd.get_entry('PaperId1', 'ReviewerId1')
        # 1 * 0.3 + 2 * 0.5 + 3 * 0.7 = 3.4
        assert pair.aggregate_score == pytest.approx(3.4)
        assert pair.conflicts == []

        pair: PaperUserScores = prd.get_entry('PaperId0', 'ReviewerId1')
        # 1 * 0.75 + 2 * 0.85 + 3 * 0.95 = 5.3
        assert pair.aggregate_score == pytest.approx(5.3)
        assert pair.conflicts == []

        # This pair is created from default info - not edges
        pair: PaperUserScores = prd.get_entry('PaperId1', 'ReviewerId0')
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
        paper_notes = [MockPaperNote('PaperId0'), MockPaperNote('PaperId1')]
        reviewers = ['ReviewerId0', 'ReviewerId1']

        edge_invitations = PaperReviewerEdgeInvitationIds(score_edge_invitation_ids)
        ae0 = MockEdge(paper_notes[0].id,reviewers[0],label='affinity', weight=0.2)
        re0 = MockEdge(paper_notes[0].id,reviewers[0],label='recommendation', weight=0.4)
        xe0 = MockEdge(paper_notes[0].id,reviewers[0],label='low', weight=0.6)
        ae1 = MockEdge(paper_notes[1].id,reviewers[1],label='affinity', weight=0.3)
        re1 = MockEdge(paper_notes[1].id,reviewers[1],label='recommendation', weight=0.5)
        xe1 = MockEdge(paper_notes[1].id,reviewers[1],label='medium', weight=0.7)
        ae2 = MockEdge(paper_notes[0].id,reviewers[1],label='affinity', weight=0.75)
        re2 = MockEdge(paper_notes[0].id,reviewers[1],label='recommendation', weight=0.85)
        xe2 = MockEdge(paper_notes[0].id,reviewers[1],label='high', weight=0.95)
        inv_to_edge_map = {'conf/affinity': [ae0, ae1, ae2],
                           'conf/recommendation': [re0, re1, re2],
                           'conf/bid': [xe0, xe1, xe2]}
        prd = MockPaperReviewerData(paper_notes, reviewers, edge_invitations=edge_invitations, score_spec=score_spec, inv_to_edge_map=inv_to_edge_map, conflict_edges=[])
        prd._load_score_map(None)


        pair: PaperUserScores = prd.get_entry('PaperId0', 'ReviewerId0')
        # 1 * 0.2 + 2 * 0.4 + 3 * 0.2 = 1.6
        assert pair.aggregate_score == pytest.approx(1.6)
        assert pair.conflicts == []
        pair: PaperUserScores = prd.get_entry('PaperId1', 'ReviewerId1')
        # 1 * 0.3 + 2 * 0.5 + 3 * 0.5 = 2.8
        assert pair.aggregate_score == pytest.approx(2.8)
        assert pair.conflicts == []

        pair: PaperUserScores = prd.get_entry('PaperId0', 'ReviewerId1')
        # 1 * 0.75 + 2 * 0.85 + 3 * 0.8 = 4.85
        assert pair.aggregate_score == pytest.approx(4.85)
        assert pair.conflicts == []

        # This pair is created from default info - not edges
        pair: PaperUserScores = prd.get_entry('PaperId1', 'ReviewerId0')
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
        paper_notes = [MockPaperNote('PaperId0'), MockPaperNote('PaperId1')]
        reviewers = ['ReviewerId0', 'ReviewerId1']

        edge_invitations = PaperReviewerEdgeInvitationIds(score_edge_invitation_ids, conflicts=conflict_edge_invitation_id)
        ae0 = MockEdge(paper_notes[0].id,reviewers[0],label='affinity', weight=0.2)
        re0 = MockEdge(paper_notes[0].id,reviewers[0],label='recommendation', weight=0.4)
        xe0 = MockEdge(paper_notes[0].id,reviewers[0],label='low', weight=0.6)
        # conflict between paper0 and reviewer 0
        conf0 = MockEdge(paper_notes[0].id,reviewers[0], label=['umass.edu', 'google.com'], weight=0)

        ae1 = MockEdge(paper_notes[1].id,reviewers[1],label='affinity', weight=0.3)
        re1 = MockEdge(paper_notes[1].id,reviewers[1],label='recommendation', weight=0.5)
        xe1 = MockEdge(paper_notes[1].id,reviewers[1],label='medium', weight=0.7)
        ae2 = MockEdge(paper_notes[0].id,reviewers[1],label='affinity', weight=0.75)
        re2 = MockEdge(paper_notes[0].id,reviewers[1],label='recommendation', weight=0.85)
        xe2 = MockEdge(paper_notes[0].id,reviewers[1],label='high', weight=0.95)
        inv_to_edge_map = {'conf/affinity': [ae0, ae1, ae2],
                           'conf/recommendation': [re0, re1, re2],
                           'conf/bid': [xe0, xe1, xe2],
                           }
        prd = MockPaperReviewerData(paper_notes, reviewers, edge_invitations=edge_invitations,
                                    score_spec=score_spec, inv_to_edge_map=inv_to_edge_map, conflict_edges=[conf0])
        prd._load_score_map(None)


        pair: PaperUserScores = prd.get_entry('PaperId0', 'ReviewerId0')
        # 1 * 0.2 + 2 * 0.4 + 3 * 0.2 = 1.6
        assert pair.aggregate_score == pytest.approx(1.6)
        assert pair.conflicts == ['umass.edu', 'google.com']
        pair: PaperUserScores = prd.get_entry('PaperId1', 'ReviewerId1')
        # 1 * 0.3 + 2 * 0.5 + 3 * 0.5 = 2.8
        assert pair.aggregate_score == pytest.approx(2.8)
        assert pair.conflicts == []

        pair: PaperUserScores = prd.get_entry('PaperId0', 'ReviewerId1')
        # 1 * 0.75 + 2 * 0.85 + 3 * 0.8 = 4.85
        assert pair.aggregate_score == pytest.approx(4.85)
        assert pair.conflicts == []

        # This pair is created from default info - not edges
        pair: PaperUserScores = prd.get_entry('PaperId1', 'ReviewerId0')
        # 1 * 0.35 + 2 * 0.66 + 3 * 0.1 = 1.97
        assert pair.aggregate_score == pytest.approx(1.97)
        assert pair.conflicts == []


    bid_translate_map2 = {
        'low': 0.2,
        'medium': 0.5,
        'high': 0.8,
        'very high': 0.93,
    }

    bid_function =  """
lambda edge: 
    if edge.label == 'low':
        return 0.2
    elif edge.label == 'moderate':
        return 0.5
    elif edge.label == 'high':
        return 0.8
    elif edge.label == 'very high':
        return 0.95
"""


    fn_with_open_stmt = "lambda x:\n\topen('file.txt','w')\n\tif x == 'low':\n\t\treturn 0.3\n\telse:\n\t\treturn 0.5"




    def test_numeric (self):
        '''
        make sure numeric score on edge is returned correctly
        :return:
        '''
        prd = MockPaperReviewerData()
        score_spec = {'weight': 1, 'default': 0.35}
        # fake edge holding a floating point weight
        e = MockEdge('PaperId','ReviewerId', None, 0.8)
        ws = prd._translate_edge_to_score(score_spec, e, None)
        assert ws == pytest.approx(0.8)

    def test_symbol_translate_map (self):
        '''
        make sure symbolic score on edge is translated correctly
        :return:
        '''
        prd = MockPaperReviewerData()
        score_spec = {'weight': 3, 'default': 0, 'translate_map': self.bid_translate_map2}
        # a fake bid edge where the label is holding the symbol
        e = MockEdge('PaperId','ReviewerId','very high', None)
        ws = prd._translate_edge_to_score(score_spec, e, None)
        assert ws == pytest.approx(0.93)

    def test_symbol_translate_fn (self):
        '''
        make sure symbolic score on edge is translated correctly
        :return:
        '''
        prd = MockPaperReviewerData()
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': self.bid_function}
        # a fake bid edge where the label is holding the symbol
        e = MockEdge('PaperId','ReviewerId','very high', None)
        ws = prd._translate_edge_to_score(score_spec, e, None)
        assert ws == pytest.approx(0.95)



    def test_no_return_value (self):
        '''
        make sure translate function that does not return anything fails
        :return:
        '''
        prd = MockPaperReviewerData()
        # translate function returns None for "mystery"
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': 'lambda x:\n\tpass'}
        e = MockEdge('PaperId','ReviewerId','mystery', None)
        with pytest.raises(TypeError):
            ws = prd._translate_edge_to_score(score_spec, e, None)

    def test_syntax_error_fn (self):
        '''
        make sure translate function with syntax error fails
        :return:
        '''
        prd = MockPaperReviewerData()
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': 'lambda x:\n\tif x == "high":\nreturn 0.3'} #indentation wrong
        e = MockEdge('PaperId','ReviewerId','mystery', None)
        with pytest.raises(SyntaxError):
            ws = prd._translate_edge_to_score(score_spec, e, None)

    def test_non_float_value (self):
        '''
        make sure translate function that returns something that can't be turned into float fails
        :return:
        '''
        prd = MockPaperReviewerData()
        # translate function returns None for "mystery"
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': 'lambda x:\n\treturn "junk"'}
        e = MockEdge('PaperId','ReviewerId','mystery', None)
        with pytest.raises(ValueError):
            ws = prd._translate_edge_to_score(score_spec, e, None)

    def test_fn_makes_illegal_call (self):
        '''
        make sure translate function which calls illegal function (open) fails
        :return:
        '''
        prd = MockPaperReviewerData()
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': self.fn_with_open_stmt}
        e = MockEdge('PaperId','ReviewerId','mystery', None)
        with pytest.raises(NameError):
            ws = prd._translate_edge_to_score(score_spec, e, None)



