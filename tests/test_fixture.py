from conftest import clean_start_conference_v2


def test_fixtures(openreview_context):
    """
    Simple test to ensure that test fixtures are working.
    """
    openreview_client = openreview_context["openreview_client_v2"]

    num_reviewers = 3
    num_papers = 3
    reviews_per_paper = 1
    conference_id = "ICLR.cc/2018/Conference"

    venue = clean_start_conference_v2(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper
    )    

    assert venue.get_id() == "ICLR.cc/2018/Conference"

