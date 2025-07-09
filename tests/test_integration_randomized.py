"""
End-to-end integration tests with OpenReview server.
"""

import json
import time
import requests
import pytest
import openreview
import logging
import datetime

from matcher.solvers import SolverException

from conftest import clean_start_conference, wait_for_status

@pytest.mark.skip
def test_integration_basic(openreview_context, celery_app, celery_session_worker):
    """
    Basic integration test. Makes use of the OpenReview Builder
    """
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    conference_id = "ICML.cc/2019/Conference"
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "scores_specification": {
            conference.get_affinity_score_id(reviewers_id): {
                "weight": 1.0,
                "default": 0.0,
            }
        },
        "status": "Initialized",
        "solver": "Randomized",
        "randomized_probability_limits": "0.5",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert response.status_code == 200

    matcher_status = wait_for_status(openreview_client, config_note.id)
    assert matcher_status.content["status"] == "Complete"
    assert "randomized_fraction_of_opt" in matcher_status.content

    paper_assignment_edges = openreview_client.get_edges_count(
        label="integration-test",
        invitation=conference.get_paper_assignment_id(
            conference.get_reviewers_id()
        ),
    )

    assert paper_assignment_edges == num_papers * reviews_per_paper

@pytest.mark.skip
def test_integration_supply_mismatch_error(
    openreview_context, celery_app, celery_session_worker
):
    """
    Basic integration test. Makes use of the OpenReview Builder
    """
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    conference_id = "ICML.cc/2021/Conference"
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 10  # impossible!
    max_papers = 1
    min_papers = 1
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "scores_specification": {
            conference.get_affinity_score_id(reviewers_id): {
                "weight": 1.0,
                "default": 0.0,
            }
        },
        "status": "Initialized",
        "solver": "Randomized",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert response.status_code == 200

    matcher_status = wait_for_status(openreview_client, config_note.id)
    assert matcher_status.content["status"] == "No Solution"
    assert (
        matcher_status.content["error_message"]
        == "Review demand (100) must be between the min review supply is (10) and max review supply is (10). Try (1) decreasing min papers (2) increasing max papers or (3) finding more reviewers"
    )

    paper_assignment_edges = openreview_client.get_edges_count(
        label="integration-test",
        invitation=conference.get_paper_assignment_id(
            conference.get_reviewers_id()
        ),
    )

    assert paper_assignment_edges == 0

@pytest.mark.skip
def test_integration_demand_out_of_supply_range_error(
    openreview_context, celery_app, celery_session_worker
):
    """
    Test to check that a No Solution is observed when demand is not in the range of min and max supply
    """
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    conference_id = "ICML.cc/2035/Conference"
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 4
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "scores_specification": {
            conference.get_affinity_score_id(reviewers_id): {
                "weight": 1.0,
                "default": 0.0,
            }
        },
        "status": "Initialized",
        "solver": "Randomized",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert response.status_code == 200

    matcher_status = wait_for_status(openreview_client, config_note.id)
    assert matcher_status.content["status"] == "No Solution"
    assert (
        matcher_status.content["error_message"]
        == "Review demand (30) must be between the min review supply is (40) and max review supply is (50). Try (1) decreasing min papers (2) increasing max papers or (3) finding more reviewers"
    )

    paper_assignment_edges = openreview_client.get_edges_count(
        label="integration-test",
        invitation=conference.get_paper_assignment_id(
            conference.get_reviewers_id()
        ),
    )

    assert paper_assignment_edges == 0

@pytest.mark.skip
def test_integration_no_scores(openreview_context, celery_app, celery_session_worker):
    """
    Basic integration test. Makes use of the OpenReview Builder
    """
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    conference_id = "ICML.cc/2020/Conference"
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "status": "Initialized",
        "solver": "Randomized",
        "allow_zero_score_assignments": "Yes",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert response.status_code == 200

    matcher_status = wait_for_status(openreview_client, config_note.id)

    config_note = openreview_client.get_note(config_note.id)
    assert matcher_status.content["status"] == "Complete"

    paper_assignment_edges = openreview_client.get_edges_count(
        label="integration-test",
        invitation=conference.get_paper_assignment_id(
            conference.get_reviewers_id()
        ),
    )

    assert paper_assignment_edges == num_papers * reviews_per_paper

@pytest.mark.skip
def test_routes_invalid_invitation(
    openreview_context, celery_app, celery_session_worker
):
    """"""
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    conference_id = "ICML.cc/2019/Conference"
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "scores_specification": {
            # conference.get_affinity_score_id(reviewers_id): {
            #     'weight': 1.0,
            #     'default': 0.0
            # },
            "<some_invalid_invitation>": {"weight": 1.0, "default": 0.0}
        },
        "status": "Initialized",
        "solver": "Randomized",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    invalid_invitation_response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert invalid_invitation_response.status_code == 404

    config_note = openreview_client.get_note(config_note.id)
    assert config_note.content["status"] == "Error"

@pytest.mark.skip
def test_routes_missing_header(openreview_context, celery_app, celery_session_worker):
    """request with missing header should response with 400"""
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    conference_id = "ICML.cc/2019/Conference"
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "scores_specification": {
            conference.get_affinity_score_id(reviewers_id): {
                "weight": 1.0,
                "default": 0.0,
            }
        },
        "status": "Initialized",
        "solver": "Randomized",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    missing_header_response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
    )
    assert missing_header_response.status_code == 400

@pytest.mark.skip
def test_routes_missing_config(openreview_context, celery_app, celery_session_worker):
    """should return 404 if config note doesn't exist"""

    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    missing_config_response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": "BAD_CONFIG_NOTE_ID"}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert missing_config_response.status_code == 404


@pytest.mark.skip  # TODO: fix the authorization so that this test passes.
def test_routes_bad_token(openreview_context, celery_app, celery_session_worker):
    """should return 400 if token is bad"""
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]
    app = openreview_context["app"]

    bad_token_response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": "BAD_CONFIG_NOTE_ID"}),
        content_type="application/json",
        headers={"Authorization": "BAD_TOKEN"},
    )
    assert bad_token_response.status_code == 400


@pytest.mark.skip  # TODO: fix authorization so that this test passes.
def test_routes_forbidden_config(
    openreview_context, celery_app, celery_session_worker
):
    """should return 403 if user does not have permission on config note"""

    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]
    app = openreview_context["app"]

    conference_id = "ICML.cc/2019/Conference"
    num_reviewers = 1
    num_papers = 1
    reviews_per_paper = 1
    max_papers = 1
    min_papers = 0
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "scores_specification": {
            conference.get_affinity_score_id(reviewers_id): {
                "weight": 1.0,
                "default": 0.0,
            }
        },
        "status": "Initialized",
        "solver": "Randomized",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    guest_client = openreview.Client(
        username="", password="", baseurl=app.config["OPENREVIEW_BASEURL"]
    )

    forbidden_response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=guest_client.headers,
    )
    assert forbidden_response.status_code == 403

@pytest.mark.skip
def test_routes_already_running_or_complete(
    openreview_context, celery_app, celery_session_worker
):
    """should return 400 if the match is already running or complete"""

    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    conference_id = "ICML.cc/2019/Conference"
    num_reviewers = 1
    num_papers = 1
    reviews_per_paper = 1
    max_papers = 1
    min_papers = 0
    alternates = 0

    conference = clean_start_conference(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = conference.get_reviewers_id()

    config = {
        "title": "integration-test",
        "user_demand": str(reviews_per_paper),
        "max_papers": str(max_papers),
        "min_papers": str(min_papers),
        "alternates": str(alternates),
        "config_invitation": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ),
        "paper_invitation": conference.get_blind_submission_id(),
        "assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id
        ),
        "deployed_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, deployed=True
        ),
        "invite_assignment_invitation": conference.get_paper_assignment_id(
            reviewers_id, invite=True
        ),
        "aggregate_score_invitation": "{}/-/Aggregate_Score".format(
            reviewers_id
        ),
        "conflicts_invitation": conference.get_conflict_score_id(reviewers_id),
        "custom_max_papers_invitation": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ),
        "match_group": reviewers_id,
        "scores_specification": {
            conference.get_affinity_score_id(reviewers_id): {
                "weight": 1.0,
                "default": 0.0,
            }
        },
        "status": "Running",
        "solver": "Randomized",
    }

    config_note = openreview.Note(
        **{
            "invitation": "{}/-/Assignment_Configuration".format(reviewers_id),
            "readers": [conference.get_id()],
            "writers": [conference.get_id()],
            "signatures": [conference.get_id()],
            "content": config,
        }
    )

    config_note = openreview_client.post_note(config_note)
    assert config_note

    already_running_response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert already_running_response.status_code == 400

    config_note = openreview_client.get_note(config_note.id)
    assert config_note.content["status"] == "Running"

    config_note.content["status"] = "Complete"
    config_note = openreview_client.post_note(config_note)
    assert config_note
    print("config note set to: ", config_note.content["status"])

    already_complete_response = test_client.post(
        "/match",
        data=json.dumps({"configNoteId": config_note.id}),
        content_type="application/json",
        headers=openreview_client.headers,
    )
    assert already_complete_response.status_code == 400
    config_note = openreview_client.get_note(config_note.id)
    assert config_note.content["status"] == "Complete"
