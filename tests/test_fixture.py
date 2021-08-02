from conftest import clean_start_conference


def test_fixtures(openreview_context):
    """
    Simple test to ensure that test fixtures are working.
    """
    openreview_client = openreview_context['openreview_client']

    num_reviewers = 3
    num_papers = 3
    reviews_per_paper = 1
    conference_id = 'ICLR.cc/2018/Conference'

    conference = clean_start_conference(
        openreview_client, conference_id, num_reviewers, num_papers, reviews_per_paper)

    assert conference.get_id() == 'ICLR.cc/2018/Conference'


def test_celery_fixtures(celery_app, celery_worker):
    @celery_app.task(bind=True)
    def mul(self, x, y):
        return x * y

    result = mul.s(4, 4).apply()
    assert result.get() == 16
