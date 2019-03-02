from flask import request, jsonify
from matcher import app
from matcher.match import Match
import tests.mock_or_client
import openreview
from exc.exceptions import NoTokenException, BadTokenException, AlreadyRunningException, AlreadyCompleteException
from matcher.fields  import Configuration

def get_client (token=None):
    baseurl = app.config['OPENREVIEW_BASEURL']
    if app.config['TESTING'] and app.config.get('USE_API'):
        email = app.config.get('OPENREVIEW_USERNAME')
        pw = app.config.get('OPENREVIEW_PASSWORD')
        return openreview.Client(baseurl=baseurl,username=email, password=pw)
    elif app.config['TESTING']:
        return tests.mock_or_client.MockORClient(baseurl=baseurl,token=token)
    else:
        return openreview.Client(baseurl=baseurl,token=token)


@app.route('/match/test')
def test():
    app.logger.info("In test")
    return "Flask is running"


@app.route('/match', methods=['POST','OPTIONS'])
def match():
    app.logger.debug("POST /match")
    res = {}
    matcher = None
    try:
        token = request.headers.get('Authorization')
        if not token:
            raise NoTokenException('No Authorization token in headers')
        # N.B. If the token is invalid, it succeeds using a guest
        client = get_client(token=token)
        params = request.json
        config_note_id = params['configNoteId']
        # TODO move status setting out of Match and into this ConfigStatus class
        # config_status = ConfigStatus(client,config_note_id)
        app.logger.debug("Request to assign reviewers for configId: " + config_note_id)
        # If the client was constructed with a bad token, the failure happens here
        config_note = client.get_note(config_note_id)
        # If the configuration is already running a matching task, do not allow another until the
        # running task is complete
        if config_note.content[Configuration.STATUS] == Configuration.STATUS_RUNNING:
            raise AlreadyRunningException('There is already a running matching task for config ' + config_note_id)
        elif config_note.content[Configuration.STATUS] == Configuration.STATUS_COMPLETE:
            raise AlreadyCompleteException('Cannot run matcher on a completed configuration ' + config_note_id)

        matcher = Match(client,config_note,app.logger)
        # runs the match task in a separate thread
        matcher.run()
    except openreview.OpenReviewException as e:
        app.logger.error('OpenReview-py error:', exc_info=True)
        # this exception type has args which is a tuple containing a list containing a dict where the type key indicates what went wrong
        err_type = e.args[0][0]['type']
        status = 500
        if err_type.lower() == 'not found':
            status = 404
        elif err_type.lower() == 'forbidden':
            status = 403
        else:
            err_type = str(e)
        res['error'] = err_type
        if matcher:
            matcher.set_status(Configuration.STATUS_ERROR,"Error: " + str(e))
        return jsonify(res) , status
    except (NoTokenException, BadTokenException, AlreadyRunningException) as e:
        app.logger.error('OpenReview-matcher error:', exc_info=True)
        res['error'] = str(e)
        if matcher:
            matcher.set_status(Configuration.STATUS_ERROR,"Error: " + str(e))
        return jsonify(res), 400

    except Exception as e:
        app.logger.error('OpenReview-matcher error:', exc_info=True)
        res['error'] = str(e)
        # TODO Shouldn't need to rely on existence of a matcher in order to set config status- Use ConfigStatus object instead.
        if matcher:
            matcher.set_status(Configuration.STATUS_ERROR,"Error: " + str(e))
        return jsonify(res), 500
    else:
        app.logger.debug("POST returns " + str(res))
        return jsonify(res)
