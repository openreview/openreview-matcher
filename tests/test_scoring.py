import pytest
from openreview import Invitation, Note, Edge
from helpers.Params import Params
from matcher.PaperReviewerData import PaperReviewerData
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges

from matcher.PaperUserScores import PaperUserScores

class MockPaperReviewerData(PaperReviewerData):
    # override superclass with a noop so its easy to instantiate and test.
    def __init__ (self):
        pass

class MockEdge:
    def __init__ (self, head, tail, label, weight):
        self.head = head
        self.tail = tail
        self.label = label
        self.weight = weight


class TestScoring:
    ''' Unit tests that check the correctness of the SimpleGraphBuilder Solver'''

    @classmethod
    def setup_class(cls):
        cls.silent = True

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

    or_function =  """
lambda edge: 
    paper_note = or_client.get_note(id=edge.head)
    reviewer = edge.tail
    title = paper_note.content['title']
    print('The paper title is ' + title)
    return 1
"""


    def fn_with_escape_formatting (self):
        return "lambda x:\nif x == 'low':\n\treturn 0.3\nelse:\n\treturn 0.5"

    def fn_with_open_stmt (self):
        return "lambda x:\n\topen('file.txt','w')\n\tif x == 'low':\n\t\treturn 0.3\n\telse:\n\t\treturn 0.5"

    def fn_unbound_var_error (self):
        return """
def edge_to_score(edge):
    if not edge:
        return     
    if edge.label == 'low':
        return 0.3
    else:
        return 0.5
"""


    # uses the or_client variable, the openreview package, and the forum_id variable.
    def fn_openreview_access (self):
        return """
lambda x:
    paper_note = or_client.get_note(id=forum_id)
    print(paper_note.content['title']
"""

    # not sure how this would be coded.   Want to intersect the subject areas of the
    # paper with the subject areas the reviewer is knowledgeable of.
    # Currently there is just one value stored in the score field which is passed to the translate fn.
    # So I'm not seeing a way to use translate_fn for doing a complex computation between a paper and a reviewer to produce a number
    # unless we start inventing pieces of syntax for giving more to these functions than just a single value coming from the score edge between
    # paper and user.

    def subject_area_function (self):
        return """
if x == 'low':
    return 0.2
elif x == 'moderate':
    return 0.5
elif x == 'high':
    return 0.8
elif x == 'very high':
    return 0.95
else:
    return 0.4
"""

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

    def test_symbol (self):
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


    def test_all_numeric_edges_given (self):
        '''
        make sure values and weights combine correctly when no defaults or translate_fns involved
        :return:
        '''
        score_spec = {'affinity': {'weight': 1, 'default': 0.35},
                      'recommendation': {'weight': 2, 'default': 0.66},
                      'xscore': {'weight': 3, 'default': 0}
                      }
        pair = PaperUserScores()
        prd = MockPaperReviewerData()
        # Do what PaperReviewData._load_scores does to get score from edges into PaperUserScores object
        e = MockEdge('PaperId','ReviewerId',label='affinity', weight=0.2)
        aff_score = prd._translate_edge_to_score(score_spec['affinity'],e,None)
        e = MockEdge('PaperId','ReviewerId',label='recommendation', weight=0.4)
        rec_score = prd._translate_edge_to_score(score_spec['recommendation'],e,None)
        e = MockEdge('PaperId','ReviewerId',label='xscore', weight=0.6)
        xscore = prd._translate_edge_to_score(score_spec['xscore'],e,None)
        # PaperReviewerData._load_scores puts scores into PaperUserScores object
        pair.add_score('affinity', aff_score)
        pair.add_score('recommendation', rec_score)
        pair.add_score('xscore', xscore)

        ws = pair.calculate_aggregrate_score(score_spec)
        # ws should be 0.2*1 + .4*2 + 0.6*3 = 2.8
        assert ws == pytest.approx(2.8)

    def test_all_numeric_default (self):
        '''
        case where no edges are given for the scores so that the defaults values are used
        :return:
        '''
        pair = PaperUserScores()
        score_spec = {'affinity': {'weight': 1, 'default': 0.35},
                      'recommendation': {'weight': 2, 'default': 0.66},
                      }
        ws = pair.calculate_aggregrate_score(score_spec)
        # ws should be 0.35*1 + .66*2 = 1.67
        assert ws == pytest.approx(1.67)

    def test_symbolic_default (self):
        '''
        case where no edge is given for a bid score translated by a function.   Default value (must be a number) will be used.
        :return:
        '''
        pair = PaperUserScores()
        score_spec = {'bid': {'weight': 2, 'default': 0.2, 'translate_fn': 'lambda x:\n\treturn 0.75'}
                      }
        ws = pair.calculate_aggregrate_score(score_spec)
        # ws should be 0.2*2 = 0.4
        assert ws == pytest.approx(0.4)

    def test_numeric_and_symbolic_edges_given (self):
        '''
        case where all edges are given for both numeric and symbolic values
        :return:
        '''
        score_spec = {'affinity': {'weight': 1, 'default': 0.35},
                      'recommendation': {'weight': 2, 'default': 0.66},
                      'bid': {'weight': 3, 'default': 0, 'translate_fn': self.bid_function}
                      }
        pair = PaperUserScores()
        prd = MockPaperReviewerData()
        # Do what PaperReviewData._load_scores does to get score from edges into PaperUserScores object
        e = MockEdge('PaperId','ReviewerId',label='affinity', weight=0.2)
        aff_score = prd._translate_edge_to_score(score_spec['affinity'],e,None)
        e = MockEdge('PaperId','ReviewerId',label='recommendation', weight=0.4)
        rec_score = prd._translate_edge_to_score(score_spec['recommendation'],e,None)
        e = MockEdge('PaperId','ReviewerId',label='high', weight=None) # bid edge
        bid_score = prd._translate_edge_to_score(score_spec['bid'],e,None)
        # PaperReviewerData._load_scores puts scores into PaperUserScores object
        pair.add_score('affinity', aff_score)
        pair.add_score('recommendation', rec_score)
        pair.add_score('bid', bid_score)

        ws = pair.calculate_aggregrate_score(score_spec)
        # ws should be 0.2*1 + .4*2 + 0.8*3 = 3.4
        assert ws == pytest.approx(3.4)


    @pytest.mark.skip
    def test_with_real_objects (self, test_util):
        '''
        make sure translate function can call openreview API
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
        conf = ConferenceConfigWithEdges(or_client, test_util.next_conference_count() , params)
        conf_id = conf.conf_ids.CONF_ID
        # add invitation for bid edge and subjectArea edge
        bid_edge_inv = Invitation(id=conf_id + '/-/bid')
        subjarea_edge_inv = Invitation(id=conf_id + '/-/subjectArea')
        bid_edge_inv = self.client.post_invitation(bid_edge_inv)
        subjarea_edge_inv = self.client.post_invitation(subjarea_edge_inv)
        prd = MockPaperReviewerData()
        score_spec = {'weight': 3, 'default': 0, 'translate_fn': self.or_function}
        # a fake bid edge where the label is holding the symbol
        e = MockEdge('BklQlHbr8N','ReviewerId','very high', None)
        ws = prd._translate_edge_to_score(score_spec, e, or_client)
        assert ws == pytest.approx(1)
