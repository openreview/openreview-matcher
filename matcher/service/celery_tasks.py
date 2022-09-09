import logging

from requests.exceptions import ConnectionError
from urllib3.exceptions import ConnectTimeoutError, RequestError

from matcher import Matcher
from matcher.core import MatcherStatus
from matcher.service.openreview_interface import (
    BaseConfigNoteInterface,
    Deployment,
)
from matcher.service.server import celery_app as celery


def on_task_failure(self, exc, task_id, args, kwargs, einfo):
    if kwargs:
        logger = kwargs["logger"]
        interface = kwargs["interface"]
        logger.warn(
            "{} task for config note {} failed.".format(
                self.name, interface.config_note.id
            )
        )
        set_error_status.apply_async(
            kwargs={"interface": interface, "logger": logger, "exc": exc},
            queue="failure",
            ignore_result=True,
        )


@celery.task(
    name="error_status",
    track_started=True,
    bind=True,
    time_limit=3600 * 24,
    autoretry_for=(Exception,),
    retry_backoff=10,
    max_retries=15,
    retry_jitter=True,
)
def set_error_status(self, interface, logger, exc):
    logger.info(
        "Setting status for config note {} to Error.".format(
            interface.config_note.id
        )
    )
    interface.set_status(MatcherStatus.ERROR, message=str(type(exc)))


@celery.task(
    name="matching",
    track_started=True,
    bind=True,
    time_limit=3600 * 24,
    on_failure=on_task_failure,
)
def run_matching(
    self,
    interface: BaseConfigNoteInterface,
    solver_class: str,
    logger: logging.Logger,
):
    logger.debug(
        "{} task received for config note {}".format(
            self.name, interface.config_note.id
        )
    )
    matcher = Matcher(
        datasource=interface, solver_class=solver_class, logger=logger
    )
    try:
        matcher.run()
        return matcher.get_status()
    except (
        ConnectionError,
        ConnectTimeoutError,
        RequestError,
        ConnectionRefusedError,
    ) as exc:
        raise self.retry(
            exc=exc, countdown=300 * (self.request.retries + 1), max_retries=3
        )


@celery.task(
    name="deployment",
    track_started=True,
    bind=True,
    time_limit=3600 * 24,
    on_failure=on_task_failure,
)
def run_deployment(
    self, interface, logger
):
    deployment = Deployment(config_note_interface=interface, logger=logger)
    try:
        deployment.run()
        return interface.config_note.content["status"]
    except (
        ConnectionError,
        ConnectTimeoutError,
        RequestError,
        ConnectionRefusedError,
    ) as exc:
        raise self.retry(
            exc=exc, countdown=300 * (self.request.retries + 1), max_retries=1
        )
