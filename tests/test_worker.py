import asyncio
import os
import signal
import time
import types

import pytest
from bullmq import Queue, UnrecoverableError
from openreview import openreview

from matcher.service import worker as worker_module
from matcher.service.job_queue import (
    MATCHING,
    enqueue,
    job_data,
    queue_options,
)
from matcher.service.openreview_interface import ConfigNoteInterfaceV2
from matcher.service.worker import (
    JobError,
    MatcherWorker,
    RetryableJobError,
    run_in_subprocess,
)
from conftest import clean_start_conference_v2, wait_for_status


def return_sum(x, y):
    return x + y


def raise_connection_refused():
    raise ConnectionRefusedError("API is down")


def raise_value_error():
    raise ValueError("bad config")


def sleep_forever():
    time.sleep(3600)


def exit_abruptly():
    os._exit(3)


def survive_stop_signals():
    os.kill(os.getpid(), signal.SIGTERM)
    os.kill(os.getpid(), signal.SIGINT)
    return "finished"


async def finished_job(config, job_id):
    queue = Queue(MATCHING, queue_options(config))
    try:
        for _ in range(50):
            state = await queue.getJobState(job_id)
            if state in ("completed", "failed"):
                job = await queue.getJob(job_id)
                return state, job.returnvalue
            await asyncio.sleep(0.1)
        return state, None
    finally:
        await queue.close()


def test_subprocess_returns_result():
    assert asyncio.run(run_in_subprocess(return_sum, (2, 3), 30)) == 5


def test_subprocess_connection_error_is_retryable():
    with pytest.raises(RetryableJobError) as error:
        asyncio.run(run_in_subprocess(raise_connection_refused, (), 30))
    assert error.value.error_type == "ConnectionRefusedError"
    assert "API is down" in str(error.value)


def test_subprocess_other_error_is_not_retryable():
    with pytest.raises(JobError) as error:
        asyncio.run(run_in_subprocess(raise_value_error, (), 30))
    assert type(error.value) is JobError
    assert error.value.error_type == "ValueError"


def test_subprocess_is_killed_after_timeout():
    with pytest.raises(JobError) as error:
        asyncio.run(run_in_subprocess(sleep_forever, (), 2))
    assert error.value.error_type == "TimeoutError"


def test_subprocess_that_exits_without_result_fails():
    with pytest.raises(JobError) as error:
        asyncio.run(run_in_subprocess(exit_abruptly, (), 30))
    assert error.value.error_type == "ProcessExited"
    assert "code 3" in str(error.value)


def test_subprocess_finishes_despite_stop_signals():
    result = asyncio.run(run_in_subprocess(survive_stop_signals, (), 30))
    assert result == "finished"


def test_worker_closed_before_running_does_not_start():
    worker = MatcherWorker({}, None)
    asyncio.run(worker.close())
    asyncio.run(asyncio.wait_for(worker.run(), 5))
    assert worker.workers == []


@pytest.fixture
def failing_worker(monkeypatch):
    def fail_with(error):
        async def run(*args):
            raise error

        monkeypatch.setattr(worker_module, "run_in_subprocess", run)

    failure_jobs = []

    async def add_job(queue, config, data):
        failure_jobs.append(data)

    monkeypatch.setattr(worker_module, "add_job", add_job)
    worker = MatcherWorker({"JOB_TIMEOUT": 30}, types.SimpleNamespace(
        debug=lambda message: None, warning=lambda message: None
    ))
    return worker, fail_with, failure_jobs


def matching_job(attempts_made):
    return types.SimpleNamespace(
        id="1",
        data={"config_note_id": "note"},
        attemptsMade=attempts_made,
        opts={"attempts": 4},
    )


def test_retryable_error_is_retried_before_last_attempt(failing_worker):
    worker, fail_with, failure_jobs = failing_worker
    fail_with(RetryableJobError("ConnectionRefusedError", "API is down"))

    with pytest.raises(RetryableJobError):
        asyncio.run(worker._run_job(MATCHING, matching_job(attempts_made=2)))
    assert failure_jobs == []


def test_retryable_error_on_last_attempt_sets_error_status(failing_worker):
    worker, fail_with, failure_jobs = failing_worker
    fail_with(RetryableJobError("ConnectionRefusedError", "API is down"))

    with pytest.raises(UnrecoverableError):
        asyncio.run(worker._run_job(MATCHING, matching_job(attempts_made=3)))
    assert failure_jobs == [
        {"config_note_id": "note", "error": "ConnectionRefusedError"}
    ]


def test_other_error_sets_error_status_without_retrying(failing_worker):
    worker, fail_with, failure_jobs = failing_worker
    fail_with(JobError("TimeoutError", "Job exceeded 30 seconds"))

    with pytest.raises(UnrecoverableError):
        asyncio.run(worker._run_job(MATCHING, matching_job(attempts_made=0)))
    assert failure_jobs == [
        {"config_note_id": "note", "error": "TimeoutError"}
    ]


def test_matching_task(openreview_context, matcher_worker):
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
        "title": {"value": "integration-test"},
        "user_demand": {"value": str(reviews_per_paper)},
        "max_papers": {"value": str(max_papers)},
        "min_papers": {"value": str(min_papers)},
        "alternates": {"value": str(alternates)},
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
        "match_group": {"value": reviewers_id},
        "scores_specification": {
            "value": {
                venue.get_affinity_score_id(reviewers_id): {
                    "weight": 1.0,
                    "default": 0.0,
                }
            }
        },
        "status": {"value": "Initialized"},
        "solver": {"value": "MinMax"},
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
    solver_class = interface.config_note.content.get("solver", "MinMax")
    job = enqueue(
        app.config,
        MATCHING,
        job_data(interface, solver_class=solver_class),
    )

    matcher_status = wait_for_status(openreview_client, config_note.id)
    assert matcher_status.content["status"]["value"] == "Complete", 'Error status: ' + matcher_status.content['error_message']['value']
    assert asyncio.run(finished_job(app.config, job.id)) == (
        "completed",
        "Complete",
    )

    paper_assignment_edges = openreview_client.get_edges_count(
        label="integration-test",
        invitation=venue.get_assignment_id(reviewers_id),
    )

    assert paper_assignment_edges == num_papers * reviews_per_paper
