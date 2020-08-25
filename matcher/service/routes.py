'''
Implements the Flask API endpoints.

TODO: could error handling be cleaner?
'''
import flask
from flask_cors import CORS
import threading
import openreview

from matcher import Matcher
from .openreview_interface import ConfigNoteInterface, ConfigNoteInterfaceError

BLUEPRINT = flask.Blueprint('match', __name__)
CORS(BLUEPRINT, supports_credentials=True)

class MatcherStatusException(Exception):
    '''Exception wrapper class for errors related to the status of the Matcher'''
    pass

def set_config_status(openreview_client, config_note_id, status, message=''):
    '''Set the status of the config note'''
    config_note = openreview_client.get_note(id=config_note_id)
    config_note.content['status'] = status
    config_note.content['error_message'] = message
    config_note = openreview_client.post_note(config_note)

@BLUEPRINT.route('/match/test')
def test():
    '''Test endpoint.'''
    flask.current_app.logger.info('In test')
    return 'OpenReview Matcher (random assignments)'

@BLUEPRINT.route('/match', methods=['POST'])
def match():
    '''Main entry point into the app. Initiates a match run'''

    flask.current_app.logger.debug('Match request received')

    result = {}

    token = flask.request.headers.get('Authorization')
    if not token:
        flask.current_app.logger.error('No Authorization token in headers')
        result['error'] = 'No Authorization token in headers'
        return flask.jsonify(result), 400
    try:
        config_note_id = flask.request.json['configNoteId']

        flask.current_app.logger.debug(
            'Request to assign reviewers for configId: {}'.format(config_note_id))

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
        if interface.config_note.content['status'] == 'Complete':
            raise MatcherStatusException('Match configured by {} is already complete'.format(config_note_id))

        solver_class = interface.config_note.content.get('solver', 'MinMax')

        flask.current_app.logger.debug('Solver class {} selected for configuration id {}'.format(solver_class, config_note_id))

        thread = threading.Thread(
            target=Matcher(
                datasource=interface,
                solver_class=solver_class,
                logger=flask.current_app.logger
            ).run
        )
        thread.start()

        flask.current_app.logger.debug('Match for configuration has started: {}'.format(config_note_id))

    except ConfigNoteInterfaceError as error_handle:
        error_type = str(error_handle)
        flask.current_app.logger.error(error_type)

        request_status = 404

        # Set status in config note only when the error is not for config note's existence itself
        if 'Config note not found' not in error_type:
            set_config_status(openreview_client, config_note_id, 'Error', message=error_type)

        result['error'] = error_type
        return flask.jsonify(result), request_status

    except MatcherStatusException as error_handle:
        flask.current_app.logger.error(str(error_handle))
        result['error'] = str(error_handle)
        return flask.jsonify(result), 400
    
    except openreview.OpenReviewException as error_handle:
        error_type = str(error_handle)
        flask.current_app.logger.error(error_type)  
        status = 500

        if 'not found' in error_type.lower():
            status = 404
        elif 'forbidden' in error_type.lower():
            status = 403

        result['error'] = error_type
        return flask.jsonify(result), status

    # For now, it seems like we need this broad Exception. How can we get rid of it?
    # pylint:disable=broad-except
    except Exception as error_handle:
        result['error'] = 'Internal server error: {}'.format(error_handle)
        return flask.jsonify(result), 500

    else:
        flask.current_app.logger.debug('POST returns ' + str(result))
        return flask.jsonify(result), 200
