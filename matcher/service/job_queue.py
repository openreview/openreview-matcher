import asyncio

from bullmq import Queue

from .openreview_interface import ConfigNoteInterfaceV1

MATCHING = "matching"
DEPLOYMENT = "deployment"
UNDEPLOYMENT = "undeployment"
FAILURE = "failure"

QUEUE_NAMES = (MATCHING, DEPLOYMENT, UNDEPLOYMENT, FAILURE)

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
    FAILURE: {
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


def job_options(config, queue_name):
    return {
        **RETRY_OPTIONS[queue_name],
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


async def add_job(queue, config, data):
    return await queue.add(queue.name, data, job_options(config, queue.name))


def enqueue(config, queue_name, data):
    """Adds a job from synchronous code, such as a Flask request handler."""

    async def add():
        queue = Queue(queue_name, queue_options(config))
        try:
            return await add_job(queue, config, data)
        finally:
            await queue.close()

    return asyncio.run(add())
