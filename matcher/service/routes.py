'''
Implements the Flask API endpoints.

TODO: could error handling be cleaner?
'''
import flask
import threading
import openreview

from matcher import Matcher
from .openreview_interface import ConfigNoteInterface

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

    token = flask.request.headers.get('Authorization')
    if not token:
        # TODO: login to the openreview client with this token
        flask.current_app.logger.error('No Authorization token in headers')
        result['error'] = 'No Authorization token in headers'
        return flask.jsonify(result), 400
    try:
        config_note_id = flask.request.json['configNoteId']

        openreview_client = openreview.Client(
            token=token,
            baseurl=flask.current_app.config['OPENREVIEW_BASEURL']
        )

        interface = ConfigNoteInterface(
            client=openreview_client,
            config_note_id=config_note_id,
            logger=flask.current_app.logger
        )

        if interface.config_note.content['status'] == 'Running':
            raise MatcherStatusException('Matcher is already running')
        else:
            interface.set_status('Running')

        flask.current_app.logger.debug(
            'Request to assign reviewers for configId: {}'.format(config_note_id))

        flask.current_app.logger.debug('Running thread: {}'.format(config_note_id))

        thread = threading.Thread(
            target=Matcher(
                datasource=interface,
                on_set_status=interface.set_status,
                on_set_assignments=interface.set_assignments,
                on_set_alternates=interface.set_alternates,
                logger=flask.current_app.logger
            ).run
        )
        thread.start()

    except openreview.OpenReviewException as error_handle:
        flask.current_app.logger.error(str(error_handle))

        error_type = error_handle.args[0][0]['type']
        print('error type: ', error_type)
        status = 500

        if 'not found' in error_type.lower():
            status = 404
        elif 'forbidden' in error_type.lower():
            status = 403
        else:
            error_type = str(error_handle)

        result['error'] = error_type

        return flask.jsonify(result), status

    except (BadTokenException, MatcherStatusException) as error_handle:
        flask.current_app.logger.error(str(error_handle))
        result['error'] = str(error_handle)


        interface.set_status('Error', str(error_handle))

        return flask.jsonify(result), 400

    # For now, it seems like we need this broad Exception. How can we get rid of it?
    # pylint:disable=broad-except
    except Exception as error_handle:
        print('broad exception triggered')
        print(error_handle)
        result['error'] = 'Internal server error: {}'.format(error_handle)
        interface.set_status('Error', 'Internal server error')
        return flask.jsonify(result), 500

    else:
        flask.current_app.logger.debug('POST returns ' + str(result))
        return flask.jsonify(result), 200
