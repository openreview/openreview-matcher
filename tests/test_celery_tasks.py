import json

from openreview import openreview

from matcher.service.celery_tasks import run_matching
from matcher.service.openreview_interface import ConfigNoteInterfaceV2
from conftest import clean_start_conference_v2, wait_for_status


def test_matching_task(openreview_context, celery_app, celery_session_worker):
    openreview_client = openreview_context["openreview_client_v2"]
    app = openreview_context["app"]

    conference_id = "ICLR.cc/2018x/Conference"
    num_reviewers = 10
    num_papers = 10
    reviews_per_paper = 3
    max_papers = 5
    min_papers = 1
    alternates = 0

    venue = clean_start_conference_v2(
        openreview_client,
        conference_id,
        num_reviewers,
        num_papers,
        reviews_per_paper,
    )   

    reviewers_id = venue.get_reviewers_id()

    config = {
        "title": { "value": "integration-test"},
        "user_demand": { "value": str(reviews_per_paper)},
        "max_papers": { "value": str(max_papers)},
        "min_papers": { "value": str(min_papers)},
        "alternates": { "value": str(alternates)},
        "config_invitation": {
            "value": "{}/-/Assignment_Configuration".format(reviewers_id)
        },
        "paper_invitation": {"value": venue.get_submission_id()},
        "assignment_invitation": {
            "value": venue.get_assignment_id(reviewers_id)
        },
        "deployed_assignment_invitation": {
            "value": venue.get_assignment_id(reviewers_id, deployed=True)
        },
        "invite_assignment_invitation": {
            "value": venue.get_assignment_id(reviewers_id, invite=True)
        },
        "aggregate_score_invitation": {
            "value": "{}/-/Aggregate_Score".format(reviewers_id)
        },
        "conflicts_invitation": {
            "value": venue.get_conflict_score_id(reviewers_id)
        },
        "custom_max_papers_invitation": {
            "value": "{}/-/Custom_Max_Papers".format(reviewers_id)
        },
        "match_group": { "value": reviewers_id},
        "scores_specification": {
            "value": {
                venue.get_affinity_score_id(reviewers_id): {
                    "weight": 1.0,
                    "default": 0.0,
                }
            }
        },
        "status": { "value": "Initialized"},
        "solver": { "value": "MinMax"},
    }

    edit = openreview_client.post_note_edit(
        invitation="{}/-/Assignment_Configuration".format(reviewers_id),
        signatures=[venue.get_id()],
        note=openreview.api.Note(content=config),
    )

    config_note = openreview_client.get_note(edit["note"]["id"])

    interface = ConfigNoteInterfaceV2(
        client=openreview_client,
        config_note_id=config_note.id,
        logger=app.logger,
    )    
    solver_class = interface.config_note.content.get("solver", {}).get("value", "MinMax")
    task = run_matching.s(interface, solver_class, app.logger).apply()

    matcher_status = wait_for_status(openreview_client, config_note.id)
    assert matcher_status.content["status"] == "Complete", 'Error status: ' + matcher_status.content['error_message']
    assert task.status == "SUCCESS"

    paper_assignment_edges = openreview_client.get_edges_count(
        label="integration-test",
        invitation=venue.get_assignment_id(reviewers_id),
    )

    assert paper_assignment_edges == num_papers * reviews_per_paper
