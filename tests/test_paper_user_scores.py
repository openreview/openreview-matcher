from matcher.PaperUserScores import PaperUserScores

class TestPaperUserScores():

    def test_empty_scores (self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores

        assert 0 == paper_user_scores.aggregate_score

    def test_single_score(self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores

        paper_user_scores.set_score('bid', 13)
        assert 13 == paper_user_scores.aggregate_score


    def test_multiple_scores(self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores
        paper_user_scores.set_score('bid', 1)
        paper_user_scores.set_score('affinity', .5)
        paper_user_scores.set_score('subjectArea', 0.56)
        assert 2.06 == paper_user_scores.aggregate_score


