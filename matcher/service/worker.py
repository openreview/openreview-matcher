"""
Processes the jobs queued by the API. Start it with:

    python -m matcher.service.worker
"""
import asyncio
import multiprocessing
import signal
import traceback

import openreview
from bullmq import Queue, UnrecoverableError, Worker
from requests.exceptions import ConnectionError
from urllib3.exceptions import ConnectTimeoutError, RequestError

from matcher import Matcher
from matcher.core import MatcherStatus
from matcher.service import create_app
from matcher.service.job_queue import (
    DEPLOYMENT,
    ERROR_STATUS,
    MATCHING,
    OPERATIONS_QUEUE,
    QUEUE_NAMES,
    UNDEPLOYMENT,
    add_job,
    queue_options,
)
from matcher.service.openreview_interface import (
    ConfigNoteInterfaceV1,
    ConfigNoteInterfaceV2,
    Deployment,
    Undeployment,
)

RETRYABLE_ERRORS = (
    ConnectionError,
    ConnectTimeoutError,
    RequestError,
    ConnectionRefusedError,
)


class JobError(Exception):
    def __init__(self, error_type, details):
        super().__init__(details)
        self.error_type = error_type


class RetryableJobError(JobError):
    pass


def build_interface(config, data, logger):
    if data["api_version"] == 1:
        client = openreview.Client(
            token=data["token"], baseurl=config["OPENREVIEW_BASEURL"]
        )
        interface_class = ConfigNoteInterfaceV1
    else:
        client = openreview.api.OpenReviewClient(
            token=data["token"], baseurl=config["OPENREVIEW_BASEURL_V2"]
        )
        interface_class = ConfigNoteInterfaceV2
    return interface_class(
        client=client, config_note_id=data["config_note_id"], logger=logger
    )


def execute_job(job_name, data, config):
    logger = create_app(config).logger
    interface = build_interface(config, data, logger)
    if job_name == MATCHING:
        matcher = Matcher(
            datasource=interface,
            solver_class=data["solver_class"],
            logger=logger,
        )
        matcher.run()
        return matcher.get_status()
    if job_name == DEPLOYMENT:
        Deployment(config_note_interface=interface, logger=logger).run()
    elif job_name == UNDEPLOYMENT:
        Undeployment(config_note_interface=interface, logger=logger).run()
    return interface.config_note.content["status"]


def set_error_status(config, data, logger):
    logger.info(
        "Setting status for config note {} to Error.".format(
            data["config_note_id"]
        )
    )
    interface = build_interface(config, data, logger)
    interface.set_status(MatcherStatus.ERROR, message=data["error"])


def _run_child(target, args, connection):
    # A stop signal sent to the whole process group must not kill a job
    # midway: the worker lets running jobs finish before it exits.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    try:
        connection.send((None, target(*args)))
    except RETRYABLE_ERRORS as error:
        connection.send(
            (RetryableJobError, (type(error).__name__, traceback.format_exc()))
        )
    except Exception as error:
        connection.send(
            (JobError, (type(error).__name__, traceback.format_exc()))
        )
    finally:
        connection.close()


def _receive(connection):
    try:
        return connection.recv()
    except EOFError:
        return None


async def run_in_subprocess(target, args, timeout):
    """
    Runs target(*args) in a fresh process, so that a job can be killed when it
    exceeds the timeout, a crash in a solver does not take the worker down,
    and the memory a solver allocates is released when the job ends.
    """
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_run_child, args=(target, args, sender))
    process.start()
    sender.close()
    try:
        outcome = await asyncio.wait_for(
            asyncio.to_thread(_receive, receiver), timeout
        )
    except asyncio.TimeoutError:
        raise JobError(
            "TimeoutError", "Job exceeded {} seconds".format(timeout)
        )
    finally:
        if process.is_alive():
            process.kill()
        await asyncio.to_thread(process.join)
        receiver.close()

    if outcome is None:
        raise JobError(
            "ProcessExited",
            "Job process exited with code {} without a result".format(
                process.exitcode
            ),
        )
    error_class, result = outcome
    if error_class:
        raise error_class(*result)
    return result


class MatcherWorker:
    def __init__(self, config, logger):
        self.config = dict(config)
        self.logger = logger
        self.workers = []
        self.operations_queue = None
        self.closing = None

    async def run(self):
        if self.closing:
            return
        options = queue_options(self.config)
        self.operations_queue = Queue(OPERATIONS_QUEUE, options)
        self.workers = [
            Worker(
                queue_name,
                self._process,
                {
                    **options,
                    "autorun": False,
                    "concurrency": self.config["WORKER_CONCURRENCY"][
                        queue_name
                    ],
                },
            )
            for queue_name in QUEUE_NAMES
        ]
        try:
            await asyncio.gather(*(worker.run() for worker in self.workers))
        finally:
            # bullmq's Worker.run() returns as soon as close() starts, before
            # its teardown is done. Callers may stop the event loop when this
            # method returns, which would leave that teardown hanging.
            await self.close()
            await self.operations_queue.close()

    async def close(self):
        if self.closing is None:
            self.closing = asyncio.ensure_future(
                asyncio.gather(*(worker.close() for worker in self.workers))
            )
        await asyncio.shield(self.closing)

    async def _process(self, job, token):
        if job.name == ERROR_STATUS:
            return await asyncio.to_thread(
                set_error_status, self.config, job.data, self.logger
            )
        return await self._run_job(job)

    async def _run_job(self, job):
        config_note_id = job.data["config_note_id"]
        self.logger.debug(
            "{} job {} received for config note {}".format(
                job.name, job.id, config_note_id
            )
        )
        try:
            return await run_in_subprocess(
                execute_job,
                (job.name, job.data, self.config),
                self.config["JOB_TIMEOUT"],
            )
        except JobError as error:
            if isinstance(error, RetryableJobError) and (
                job.attemptsMade + 1 < job.opts["attempts"]
            ):
                self.logger.warning(
                    "{} job for config note {} will be retried: {}".format(
                        job.name, config_note_id, error.error_type
                    )
                )
                raise
            self.logger.warning(
                "{} job for config note {} failed: {}".format(
                    job.name, config_note_id, error
                )
            )
            await add_job(
                self.operations_queue,
                self.config,
                ERROR_STATUS,
                {**job.data, "error": error.error_type},
            )
            raise UnrecoverableError(str(error)) from error


def main():
    app = create_app()
    worker = MatcherWorker(app.config, app.logger)

    async def run():
        loop = asyncio.get_running_loop()
        for signal_number in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                signal_number, lambda: asyncio.ensure_future(worker.close())
            )
        await worker.run()

    asyncio.run(run())


if __name__ == "__main__":
    # Run from the importable module rather than __main__, so the functions
    # and exceptions pickled to and from job processes resolve by their
    # real module path.
    from matcher.service.worker import main as worker_main

    worker_main()
