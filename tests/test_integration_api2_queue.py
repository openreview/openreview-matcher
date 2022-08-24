"""
End-to-end integration tests with OpenReview server and Celery task queue.
"""

import json
import time

import openreview

from conftest import clean_start_conference_v2, wait_for_status


def test_integration_basic(openreview_context, celery_app, celery_worker):
    """
    Basic integration test. Makes use of the OpenReview Builder
    """
    openreview_client = openreview_context["openreview_client_v2"]
    test_client = openreview_context["test_client"]

    num_reviewers = 20
    num_papers = 20
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    note_ids = []
    conference_id = "AKBD.ws/2030/Conference"
    venue = clean_start_conference_v2(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )

    reviewers_id = venue.get_reviewers_id()

    config = {
        "title": {"value": "integration-test" },
        "user_demand": {"value": str(reviews_per_paper) },
        "max_papers": {"value": str(max_papers) },
        "min_papers": {"value": str(min_papers) },
        "alternates": {"value": str(alternates) },
        "config_invitation": {"value": "{}/-/Assignment_Configuration".format(
            reviewers_id
        ) },
        "paper_invitation": {"value": venue.get_submission_id() },
        "assignment_invitation": {"value": venue.get_paper_assignment_id(
            reviewers_id
        ) },
        "deployed_assignment_invitation": {"value": venue.get_paper_assignment_id(
            reviewers_id, deployed=True
        ) },
        "invite_assignment_invitation": {"value": venue.get_paper_assignment_id(
            reviewers_id, invite=True
        ) },
        "aggregate_score_invitation": {"value": "{}/-/Aggregate_Score".format(
            reviewers_id
        ) },
        "conflicts_invitation": {"value": venue.get_conflict_score_id(reviewers_id) },
        "custom_max_papers_invitation": {"value": "{}/-/Custom_Max_Papers".format(
            reviewers_id
        ) },
        "match_group": {"value": reviewers_id },
        "scores_specification": {"value": {
            venue.get_affinity_score_id(reviewers_id): {
                "weight": 1.0,
                "default": 0.0,
            }
        } },
        "status": {"value": "Initialized" },
        "solver": {"value": "FairFlow" },
    }

    for i in range(10):
        config_note = openreview_client.post_note_edit(
            invitation="{}/-/Assignment_Configuration".format(reviewers_id),
            signatures=[venue.get_id()],
            note=openreview.api.Note(
                content=config
            )
        )
        assert config_note
        note_ids.append(config_note['note']['id'])


    for note_id in note_ids:
        response = test_client.post(
            "/match",
            data=json.dumps({"configNoteId": note_id}),
            content_type="application/json",
            headers=openreview_client.headers,
        )
        assert response.status_code == 200

    for note_id in note_ids:
        matcher_status = wait_for_status(openreview_client, note_id, api_version=2)
        assert matcher_status.content["status"]["value"] == "Complete"
