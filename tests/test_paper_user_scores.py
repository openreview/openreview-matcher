from matcher.PaperUserScores import PaperUserScores

class TestPaperUserScores():

    def test_empty_scores (self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores

        assert 0 == paper_user_scores.aggregate_score

    def test_single_score(self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores

        paper_user_scores.add_score('bid', 1)
        score_spec = {'conf_stuff/bid': {'weight': 2, 'default': 0}}
        paper_user_scores.calculate_aggregrate_score(score_spec)
        assert 2 == paper_user_scores.aggregate_score


    def test_multiple_scores(self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores
        score_spec = {'conf/bid': {'weight': 2, 'default': 0},
                      'conf/affinity': {'weight': 3, 'default': 1},
                      'conf/subjectArea': {'weight': 4, 'default': 2}}
        paper_user_scores.add_score('bid', 1)
        paper_user_scores.add_score('affinity', .5)
        paper_user_scores.add_score('subjectArea', 0.56)
        paper_user_scores.calculate_aggregrate_score(score_spec)
        # 1*2 + .5*3 + .56*4 = 5.74
        assert 5.74 == paper_user_scores.aggregate_score


