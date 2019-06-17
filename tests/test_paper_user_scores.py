from matcher.PaperUserScores import PaperUserScores

class TestPaperUserScores():

    def test_empty_scores (self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores

        assert 0 == paper_user_scores.get_aggregate_score()

    def test_single_score(self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores

        paper_user_scores.add_score('bid', 1)
        assert 1 == paper_user_scores.get_aggregate_score()

        paper_user_scores.add_score('bid', 1.5)
        assert 1.5 == paper_user_scores.get_aggregate_score()

    def test_multiple_scores(self):

        paper_user_scores = PaperUserScores()
        assert paper_user_scores

        paper_user_scores.add_score('bid', 1)
        paper_user_scores.add_score('affinity', 0)
        paper_user_scores.add_score('subjectArea', 0.56)
        assert 1.56 == paper_user_scores.get_aggregate_score()


