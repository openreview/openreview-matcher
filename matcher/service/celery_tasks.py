import logging

from matcher import Matcher
from matcher.core import MatcherStatus
from matcher.service.openreview_interface import ConfigNoteInterface, Deployment
from matcher.service.server import celery_app as celery


@celery.task(name='matching', track_started=True, bind=True, time_limit=3600 * 24)
def run_matching(self, interface: ConfigNoteInterface, solver_class: str, logger: logging.Logger):
    matcher = Matcher(
        datasource=interface,
        solver_class=solver_class,
        logger=logger
    )
    try:
        matcher.run()
    except Exception as exc:
        matcher.logger.error('Error: {}'.format(exc))
        matcher.set_status(MatcherStatus.ERROR, message=exc)


@celery.task(name='deployment', track_started=True, bind=True, time_limit=3600 * 24)
def run_deployment(self, interface: ConfigNoteInterface, logger: logging.Logger):
    deployment = Deployment(
        config_note_interface=interface,
        logger=logger
    )
    try:
        deployment.run()
    except Exception as exc:
        deployment.logger.error('Error: {}'.format(exc))
        self.config_note_interface.set_status(MatcherStatus.DEPLOYMENT_ERROR, message=exc)
