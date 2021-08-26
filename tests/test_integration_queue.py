"""
End-to-end integration tests with OpenReview server and Celery task queue.
"""

import json
import time

import openreview

from conftest import clean_start_conference, wait_for_status


def test_integration_basic(openreview_context, celery_app, celery_worker):
    """
    Basic integration test. Makes use of the OpenReview Builder
    """
    openreview_client = openreview_context["openreview_client"]
    test_client = openreview_context["test_client"]

    num_reviewers = 20
    num_papers = 20
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    note_ids = []
    conference_id = "AKBC.ws/2030/Conference"
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
        "solver": "FairFlow",
    }

    for i in range(10):
        config_note = openreview.Note(
            **{
                "invitation": "{}/-/Assignment_Configuration".format(
                    reviewers_id
                ),
                "readers": [conference.get_id()],
                "writers": [conference.get_id()],
                "signatures": [conference.get_id()],
                "content": config,
            }
        )

        config_note = openreview_client.post_note(config_note)
        assert config_note

        note_ids.append(config_note.id)

    for note_id in note_ids:
        response = test_client.post(
            "/match",
            data=json.dumps({"configNoteId": note_id}),
            content_type="application/json",
            headers=openreview_client.headers,
        )
        assert response.status_code == 200

    for note_id in note_ids:
        matcher_status = wait_for_status(openreview_client, note_id)
        assert matcher_status.content["status"] == "Complete"
