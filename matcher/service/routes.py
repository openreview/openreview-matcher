"""
Implements the Flask API endpoints.

TODO: could error handling be cleaner?
"""
import flask
import openreview
from flask_cors import CORS

from .openreview_interface import ConfigNoteInterfaceV1, ConfigNoteInterfaceV2
from ..core import MatcherStatus

BLUEPRINT = flask.Blueprint("match", __name__)
CORS(BLUEPRINT, supports_credentials=True)


class MatcherStatusException(Exception):
    """Exception wrapper class for errors related to the status of the Matcher"""

    pass


@BLUEPRINT.route("/match/test")
def test():
    """Test endpoint."""
    flask.current_app.logger.info("In test")
    return "OpenReview Matcher (random assignments)"


@BLUEPRINT.route("/match", methods=["POST"])
def match():
    """Main entry point into the app. Initiates a match run"""

    flask.current_app.logger.debug("Match request received")
    result = {}
    token = flask.request.headers.get("Authorization")
    if not token:
        flask.current_app.logger.error("No Authorization token in headers")
        result["error"] = "No Authorization token in headers"
        return flask.jsonify(result), 400
    try:
        config_note_id = flask.request.json["configNoteId"]

        flask.current_app.logger.debug(
            "Request to assign reviewers for configId: {}".format(
                config_note_id
            )
        )

        openreview_client = openreview.Client(
            token=token, baseurl=flask.current_app.config["OPENREVIEW_BASEURL"]
        )
        openreview_client_v2 = openreview.api.OpenReviewClient(
            token=token,
            baseurl=flask.current_app.config["OPENREVIEW_BASEURL_V2"],
        )

        try:
            openreview_client.get_note(config_note_id)
            interface = ConfigNoteInterfaceV1(
                client=openreview_client,
                config_note_id=config_note_id,
                logger=flask.current_app.logger,
            )
        except openreview.OpenReviewException as e:
            if "notfound" in str(e).lower():
                openreview_client_v2.get_note(config_note_id)
                interface = ConfigNoteInterfaceV2(
                    client=openreview_client_v2,
                    config_note_id=config_note_id,
                    logger=flask.current_app.logger,
                )
            else:
                raise e
        interface.validate_group(interface.match_group)
        openreview_client.impersonate(interface.venue_id)

        if interface.config_note.content["status"] == "Running":
            raise MatcherStatusException("Matcher is already running")
        if interface.config_note.content["status"] == "Complete":
            raise MatcherStatusException(
                "Match configured by {} is already complete".format(
                    config_note_id
                )
            )
        if interface.config_note.content["status"] == "Deploying":
            raise MatcherStatusException(
                "Match configured by {} is being deployed".format(
                    config_note_id
                )
            )
        if interface.config_note.content["status"] == "Deployed":
            raise MatcherStatusException(
                "Match configured by {} is already deployed".format(
                    config_note_id
                )
            )
        if interface.config_note.content["status"] == "Queued":
            raise MatcherStatusException(
                "Match configured by {} is already in queue.".format(
                    config_note_id
                )
            )

        solver_class = interface.config_note.content.get("solver", "MinMax")

        flask.current_app.logger.debug(
            "Solver class {} selected for configuration id {}".format(
                solver_class, config_note_id
            )
        )

        interface.set_status(MatcherStatus.QUEUED)

        from .celery_tasks import run_matching

        run_matching.apply_async(
            kwargs={
                "interface": interface,
                "solver_class": solver_class,
                "logger": flask.current_app.logger,
            },
            queue="matching",
            ignore_result=False,
            task_id=config_note_id,
        )

        flask.current_app.logger.debug(
            "Match for configuration has been queued: {}".format(
                config_note_id
            )
        )

    except openreview.OpenReviewException as exception:
        flask.current_app.logger.error(str(exception))

        error = exception.args[0]

        if isinstance(error, dict):
            status = error.get("status", 500)
            result = error
        else:
            status = 500

            if "not found" in error.lower():
                status = 404
                result["name"] = "NotFoundError"
            elif "forbidden" in error.lower():
                status = 403
                result["name"] = "ForbiddenError"

            result["message"] = error
        return flask.jsonify(result), status

    except MatcherStatusException as error_handle:
        flask.current_app.logger.error(str(error_handle))
        result["error"] = str(error_handle)
        return flask.jsonify(result), 400

    # For now, it seems like we need this broad Exception. How can we get rid of it?
    # pylint:disable=broad-except
    except Exception as error_handle:
        result["error"] = "Internal server error: {}".format(error_handle)
        return flask.jsonify(result), 500

    else:
        flask.current_app.logger.debug("POST returns " + str(result))
        return flask.jsonify(result), 200


@BLUEPRINT.route("/deploy", methods=["POST"])
def deploy():

    flask.current_app.logger.debug("Deploy request received")

    result = {}

    token = flask.request.headers.get("Authorization")
    if not token:
        flask.current_app.logger.error("No Authorization token in headers")
        result["error"] = "No Authorization token in headers"
        return flask.jsonify(result), 400
    try:
        config_note_id = flask.request.json["configNoteId"]

        flask.current_app.logger.debug(
            "Request to deploy reviewers for configId: {}".format(
                config_note_id
            )
        )

        openreview_client = openreview.Client(
            token=token, baseurl=flask.current_app.config["OPENREVIEW_BASEURL"]
        )
        openreview_client_v2 = openreview.api.OpenReviewClient(
            token=token,
            baseurl=flask.current_app.config["OPENREVIEW_BASEURL_V2"],
        )

        flask.current_app.logger.debug("try to get configuration note")
        try:
            openreview_client.get_note(config_note_id)
            interface = ConfigNoteInterfaceV1(
                client=openreview_client,
                config_note_id=config_note_id,
                logger=flask.current_app.logger,
            )
        except openreview.OpenReviewException as e:
            if "notfound" in str(e).lower():
                openreview_client_v2.get_note(config_note_id)
                interface = ConfigNoteInterfaceV2(
                    client=openreview_client_v2,
                    config_note_id=config_note_id,
                    logger=flask.current_app.logger,
                )
            else:
                raise e

        flask.current_app.logger.debug("interface is set")

        if interface.config_note.content["status"] not in [
            "Complete",
            "Deployment Error",
        ]:
            raise MatcherStatusException(
                "Matcher configuration is not complete"
            )

        from .celery_tasks import run_deployment

        run_deployment.apply_async(
            kwargs={
                "interface": interface,
                "logger": flask.current_app.logger,
            },
            queue="deployment",
            ignore_result=False,
            task_id=config_note_id,
        )

        flask.current_app.logger.debug(
            "Deployment for configuration has started: {}".format(
                config_note_id
            )
        )

    except openreview.OpenReviewException as exception:
        flask.current_app.logger.error(str(exception))

        error = exception.args[0]

        if isinstance(error, dict):
            status = error.get("status", 500)
            result = error
        else:
            status = 500

            if "not found" in error.lower():
                status = 404
                result["name"] = "NotFoundError"
            elif "forbidden" in error.lower():
                status = 403
                result["name"] = "ForbiddenError"

            result["message"] = error
        return flask.jsonify(result), status

    except MatcherStatusException as error_handle:
        flask.current_app.logger.error(str(error_handle))
        result["error"] = str(error_handle)
        return flask.jsonify(result), 400

    # For now, it seems like we need this broad Exception. How can we get rid of it?
    # pylint:disable=broad-except
    except Exception as error_handle:
        result["error"] = "Internal server error: {}".format(error_handle)
        return flask.jsonify(result), 500

    else:
        flask.current_app.logger.debug("POST returns " + str(result))
        return flask.jsonify(result), 200

@BLUEPRINT.route("/undeploy", methods=["POST"])
def deploy():

    flask.current_app.logger.debug("Undeploy request received")

    result = {}

    token = flask.request.headers.get("Authorization")
    if not token:
        flask.current_app.logger.error("No Authorization token in headers")
        result["error"] = "No Authorization token in headers"
        return flask.jsonify(result), 400
    try:
        config_note_id = flask.request.json["configNoteId"]

        flask.current_app.logger.debug(
            "Request to undeploy reviewers for configId: {}".format(
                config_note_id
            )
        )

        openreview_client = openreview.Client(
            token=token, baseurl=flask.current_app.config["OPENREVIEW_BASEURL"]
        )
        openreview_client_v2 = openreview.api.OpenReviewClient(
            token=token,
            baseurl=flask.current_app.config["OPENREVIEW_BASEURL_V2"],
        )

        flask.current_app.logger.debug("try to get configuration note")
        try:
            openreview_client.get_note(config_note_id)
            raise MatcherStatusException("Undeploy not supported for API 1 venues")
        except openreview.OpenReviewException as e:
            if "notfound" in str(e).lower():
                openreview_client_v2.get_note(config_note_id)
                interface = ConfigNoteInterfaceV2(
                    client=openreview_client_v2,
                    config_note_id=config_note_id,
                    logger=flask.current_app.logger,
                )
            else:
                raise e

        flask.current_app.logger.debug("interface is set")

        if interface.config_note.content["status"] not in [
            "Deployed",
            "Undeployment Error",
        ]:
            raise MatcherStatusException(
                "Matcher configuration status is not Deployed"
            )

        from .celery_tasks import run_undeployment

        run_undeployment.apply_async(
            kwargs={
                "interface": interface,
                "logger": flask.current_app.logger,
            },
            queue="undeployment",
            ignore_result=False,
            task_id=config_note_id,
        )

        flask.current_app.logger.debug(
            "Undeployment for configuration has started: {}".format(
                config_note_id
            )
        )

    except openreview.OpenReviewException as exception:
        flask.current_app.logger.error(str(exception))

        error = exception.args[0]

        if isinstance(error, dict):
            status = error.get("status", 500)
            result = error
        else:
            status = 500

            if "not found" in error.lower():
                status = 404
                result["name"] = "NotFoundError"
            elif "forbidden" in error.lower():
                status = 403
                result["name"] = "ForbiddenError"

            result["message"] = error
        return flask.jsonify(result), status

    except MatcherStatusException as error_handle:
        flask.current_app.logger.error(str(error_handle))
        result["error"] = str(error_handle)
        return flask.jsonify(result), 400

    # For now, it seems like we need this broad Exception. How can we get rid of it?
    # pylint:disable=broad-except
    except Exception as error_handle:
        result["error"] = "Internal server error: {}".format(error_handle)
        return flask.jsonify(result), 500

    else:
        flask.current_app.logger.debug("POST returns " + str(result))
        return flask.jsonify(result), 200
