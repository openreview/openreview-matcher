from flask import request, jsonify
from threading import Thread
from matcher import app
from matcher.decorators import crossdomain
from matcher.match import match_task
import tests.mock_or_client
import openreview
from exc.exceptions import NoTokenException, BadTokenException

def get_client (baseurl=None,username=None,password=None,token=None):
    if app.config['TESTING']:
        return tests.mock_or_client.MockORClient(baseurl=baseurl,username=username,password=password,token=token)
    else:
        return openreview.Client(baseurl=baseurl,username=username,password=password,token=token)


@app.route('/match/test')
def test():
    app.logger.info("In test")
    return "Flask is running"


@app.route('/match', methods=['POST','OPTIONS'])
@crossdomain(origin='*', headers=['Authorization'])
def match():
    app.logger.debug("POST /match")
    res = {}
    try:
        token = request.headers.get('Authorization')
        if not token:
            raise NoTokenException('No Authorization token in headers')
        # N.B. If the token is invalid, it succeeds using a guest
        client = get_client(token=token)
        params = request.json
        configNoteId = params['configNoteId']
        app.logger.debug("Request to assign reviewers for configId: " + configNoteId)
        # If the client was constructed with a bad token, the failure happens here
        config_note = client.get_note(configNoteId)
        config_note.content['status'] = 'queued'
        config_note = client.post_note(config_note)

        args = (config_note, client)
        # TODO may want to replace threading with a task queue such as provided by RQ.
        match_thread = Thread(
            target=match_task,
            args=args
        )
        match_thread.start()

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
        return jsonify(res) , status
    except (NoTokenException, BadTokenException) as e:
        app.logger.error('OpenReview-matcher error:', exc_info=True)
        res['error'] = str(e)
        return jsonify(res), 400

    except Exception as e:
        app.logger.error('OpenReview-matcher error:', exc_info=True)
        res['error'] = str(e)
        return jsonify(res), 500

    else:
        app.logger.debug("POST returns " + str(res))
        return jsonify(res)
