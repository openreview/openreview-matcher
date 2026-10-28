import asyncio

from bullmq import Queue

from .openreview_interface import ConfigNoteInterfaceV1

MATCHING_QUEUE = "matching"
# BullMQ names its Redis connections after the queue, and Redis rejects
# connection names with spaces.
OPERATIONS_QUEUE = "matching-operations"

QUEUE_NAMES = (MATCHING_QUEUE, OPERATIONS_QUEUE)

MATCHING = "matching"
DEPLOYMENT = "deployment"
UNDEPLOYMENT = "undeployment"
ERROR_STATUS = "error status"

# Matching runs can take hours, so they get a queue of their own and cannot
# hold up the short jobs.
JOB_QUEUES = {
    MATCHING: MATCHING_QUEUE,
    DEPLOYMENT: OPERATIONS_QUEUE,
    UNDEPLOYMENT: OPERATIONS_QUEUE,
    ERROR_STATUS: OPERATIONS_QUEUE,
}

RETRY_OPTIONS = {
    MATCHING: {
        "attempts": 4,
        "backoff": {"type": "exponential", "delay": 300_000},
    },
    DEPLOYMENT: {
        "attempts": 2,
        "backoff": {"type": "fixed", "delay": 300_000},
    },
    UNDEPLOYMENT: {
        "attempts": 2,
        "backoff": {"type": "fixed", "delay": 300_000},
    },
    ERROR_STATUS: {
        "attempts": 10,
        "backoff": {"type": "exponential", "delay": 10_000},
    },
}


def queue_options(config):
    return {
        "prefix": config["BULLMQ_PREFIX"],
        "connection": {
            "host": config["REDIS_ADDR"],
            "port": config["REDIS_PORT"],
            "db": config["REDIS_DB"],
        },
    }


def job_options(config, job_name):
    return {
        **RETRY_OPTIONS[job_name],
        "removeOnComplete": {"age": config["BULLMQ_REMOVE_ON_COMPLETE_AGE"]},
        "removeOnFail": {"age": config["BULLMQ_REMOVE_ON_FAIL_AGE"]},
    }


def job_data(interface, **extra):
    """
    The worker rebuilds the interface from this data, so it carries the
    interface's token: for API 2 that is the venue impersonation token.
    """
    return {
        "config_note_id": interface.config_note.id,
        "api_version": 1
        if isinstance(interface, ConfigNoteInterfaceV1)
        else 2,
        "token": interface.client.token,
        **extra,
    }


async def add_job(queue, config, job_name, data):
    return await queue.add(job_name, data, job_options(config, job_name))


def enqueue(config, job_name, data):
    """Adds a job from synchronous code, such as a Flask request handler."""

    async def add():
        queue = Queue(JOB_QUEUES[job_name], queue_options(config))
        try:
            return await add_job(queue, config, job_name, data)
        finally:
            await queue.close()

    return asyncio.run(add())
