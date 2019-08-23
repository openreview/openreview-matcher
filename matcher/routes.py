'''
Implements the Flask API endpoints.
'''
import json
import flask
import openreview

from .matcher import Matcher
from .matcher_client import MatcherClient

BLUEPRINT = flask.Blueprint('match', __name__)

class BadTokenException(Exception):
    '''Exception wrapper class for errors related to the user token'''
    pass

class MatcherStatusException(Exception):
    '''Exception wrapper class for errors related to the status of the Matcher'''
    pass

@BLUEPRINT.route('/match/test')
def test():
    '''Test endpoint.'''
    flask.current_app.logger.info('In test')
    return 'Flask is running'

@BLUEPRINT.route('/match', methods=['POST', 'OPTIONS'])
def match():
    '''Main entry point into the app. Initiates a match run'''

    flask.current_app.logger.debug('Match request received')

    result = {}
    matcher = None

    token = flask.request.headers.get('Authorization')
    if not token:
        flask.current_app.logger.error('No Authorization token in headers')
        result['error'] = 'No Authorization token in headers'
        return flask.jsonify(result), 400

    try:
        params = flask.request.json
        config_note_id = params['configNoteId']

        client = MatcherClient(
            username=flask.current_app.config['OPENREVIEW_USERNAME'],
            password=flask.current_app.config['OPENREVIEW_PASSWORD'],
            baseurl=flask.current_app.config['OPENREVIEW_BASEURL'],
            config_id=config_note_id,
            logger=flask.current_app.logger
        )
        flask.current_app.logger.debug('Matcher client instantiated {}'.format(
            client.config_note.id))

        if client.config_note.content['status'] == 'Running':
            raise MatcherStatusException('Matcher is already running')
        else:
            client.set_status('Running')

        flask.current_app.logger.debug(
            'Request to assign reviewers for configId: {}'.format(config_note_id))

        matcher = Matcher(
            client,
            client.config_note.content,
            logger=flask.current_app.logger
        )

        flask.current_app.logger.debug('Running thread: {}'.format(config_note_id))

        matcher.run_thread()

    except openreview.OpenReviewException as error_handle:
        flask.current_app.logger.error(str(error_handle))

        error_type = error_handle.args[0][0]['type']

        status = 500

        if error_type.lower() == 'not found':
            status = 404
        elif error_type.lower() == 'forbidden':
            status = 403
        else:
            error_type = str(error_handle)

        result['error'] = error_type

        if matcher:
            client.set_status('Error', str(error_handle))

        return flask.jsonify(result), status

    except (BadTokenException, MatcherStatusException) as error_handle:
        flask.current_app.logger.error(str(error_handle))
        result['error'] = str(error_handle)

        if matcher:
            client.set_status('Error', str(error_handle))

        return flask.jsonify(result), 400

    except Exception:
        result['error'] = 'Internal server error'
        client.set_status('Error', 'Internal server error')
        return flask.jsonify(result), 500

    else:
        flask.current_app.logger.debug('POST returns ' + str(result))
        return flask.jsonify(result), 200
