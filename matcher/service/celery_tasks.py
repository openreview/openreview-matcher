import logging
import flask
from celery import Task

from matcher import Matcher
from matcher.core import MatcherStatus
from matcher.service.openreview_interface import ConfigNoteInterface
from matcher.service.server import celery


class BaseTask(Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        flask.current_app.logger.warning(self.name)
        flask.current_app.logger.warning('{0!r} failed: {1!r}'.format(task_id, exc))


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
        matcher.logger.DEBUG('Error={}'.format(exc))
        matcher.set_status(MatcherStatus.ERROR, message=exc)
