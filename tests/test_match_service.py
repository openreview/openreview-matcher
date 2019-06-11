import json
import matcher
import pytest

# Tests the match service by calling the flask endpoint with a variety of erroneous inputs.  Tests verify that correct error codes
# are returned.   The matcher app is configured so that it uses a mock openreview-py object

def post_json(client, url, json_dict, headers=None):
    """Send dictionary json_dict as a json to the specified url """
    config_note = json.dumps(json_dict)
    if headers:
        return client.post(url, data=config_note, content_type='application/json', headers=headers)
    else:
        return client.post(url, data=config_note, content_type='application/json')

def json_of_response(response):
    """Decode json from response"""
    return json.loads(response.data.decode('utf8'))


# N.B.  The app we are testing uses a logger that generates error messages when given bad inputs.  This test fixture does just that.
# It verifies that bad inputs result in correct error status returns.  However you will see stack dumps which are also produced by the logger
# These stack dumps do not represent test cases that are failing!
class TestMatchService():

    # called once at beginning of suite
    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    # called at the beginning of each test
    # This uses the test_client() which builds the Flask app and runs it for testing.  It does not
    # start it in such a way that the app initializes correctly (i.e. by calling matcher/app.py) so
    # we have to set a couple things correctly for the testing context: logging disabled and tell it where
    # the openreview base url is.
    def setup (self):
        self.app = matcher.app.test_client()
        self.app.testing = True
        # Sets the webapp up so that it will switch to using the mock OR client
        matcher.app.testing = True
        # Turn off logging in the web app so that tests run with a clean console
        matcher.app.logger.disabled = True
        matcher.app.logger.parent.disabled = True
        # or_baseurl = os.getenv('OPENREVIEW_BASEURL')
        or_baseurl = 'http://localhost:3000'
        assert or_baseurl != None and or_baseurl != ''
        matcher.app.config['OPENREVIEW_BASEURL'] = or_baseurl
        matcher.app.config['USE_API'] = False

    def teardown (self):
        pass

    # A valid token and a valid config note id which is associated with meta data that the matcher can run with to produce results.
    # The config note of this test points to meta data for ICLR.  These tokens aren't easy to create in this test code though so
    # we don't do testing with valid inputs.  Instead we mock the openreview.Client class (see mock_or_client.py) so it will behave
    # as if all the calls to the API are valid.
    '''
    def test_valid_inputs(self):
        # TODO the headers are not working correctly when it reaches the endpoint
        response = post_json(self.app, '/match', {"configNoteId": self.config_note.id},
                             headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7Il9pZCI6IjViMDA2MDk5NzEyNjFiNWU0MGM2NzZjMyIsImlkIjoiT3BlblJldmlldy5uZXQiLCJlbWFpbGFibGUiOmZhbHNlLCJjZGF0ZSI6MTUzMTE3MDUyNzQ3NiwiZGRhdGUiOm51bGwsInRtZGF0ZSI6MTUzMTE3MDUyNzY4NSwidGRkYXRlIjpudWxsLCJ0YXV0aG9yIjoiT3BlblJldmlldy5uZXQiLCJzaWduYXR1cmVzIjpbIn5TdXBlcl9Vc2VyMSJdLCJzaWduYXRvcmllcyI6WyJPcGVuUmV2aWV3Lm5ldCJdLCJyZWFkZXJzIjpbIk9wZW5SZXZpZXcubmV0Il0sIm5vbnJlYWRlcnMiOltdLCJ3cml0ZXJzIjpbIk9wZW5SZXZpZXcubmV0Il0sIm1lbWJlcnMiOlsiflN1cGVyX1VzZXIxIl0sInByb2ZpbGUiOnsiaWQiOiJ-U3VwZXJfVXNlcjEiLCJmaXJzdCI6IlN1cGVyIiwibWlkZGxlIjoiIiwibGFzdCI6IlVzZXIiLCJlbWFpbHMiOlsib3BlbnJldmlldy5uZXQiXX19LCJkYXRhIjp7fSwiaXNzIjoib3BlbnJldmlldyIsIm5iZiI6MTUzOTcxMjk3NSwiaWF0IjoxNTM5NzEyOTc1LCJleHAiOjE1Mzk3OTkzNzV9.5Xodx6nzLmmZ6ECFPvh2AyKDqJ5JThNIRQbC5Ol0eKQ'})

        # response_json = json_of_response(response)
        assert response.status_code == 200
        # not sure how to take apart the json in response,  Its a string with a dict inside a list that has
        # the stuff from OpenReviewException
    '''


    # The Authorization header is missing and passed along with a working configNoteId.   Should get back a 400
    def test_missing_auth_header (self):
        response = post_json(self.app, '/match', {'configNoteId': 'ok'},
                             headers={'a': 'b'})
        assert response.status_code == 400


    # An invalid token is passed along with a working configNoteId.   Should get back a 400
    def test_invalid_token (self):
        response = post_json(self.app, '/match', {'configNoteId': 'ok'},
                             headers={'Authorization': 'Bearer BOGUS.TOKEN'})
        assert response.status_code == 400

    # A valid token is passed but a config note id that generates an internal error in OR client.   Should get back a 500 indicating violation
    def test_internal_error (self):
        response = post_json(self.app, '/match', {'configNoteId': 'internal error'},
                             headers={'Authorization': 'Bearer Valid'})
        assert response.status_code == 500


    # A valid token is passed but a config note id that has forbidden access.   Should get back a 403 indicating violation
    def test_forbidden_config (self):
        response = post_json(self.app, '/match', {'configNoteId': 'forbidden'},
                             headers={'Authorization': 'Bearer Valid'})
        assert response.status_code == 403

    
    # A valid token is passed but an invalid config note id.   Should get back a 404 indicating resource not found
    def test_nonExistent_config (self):
        response = post_json(self.app, '/match', {'configNoteId': 'nonExist'},
                             headers={'Authorization': 'Bearer Valid'})
        assert response.status_code == 404

    # Valid inputs except that the task is already running which should result in a 400 error
    def test_running_task (self):
        response = post_json(self.app, '/match', {'configNoteId': 'already_running'},
                             headers={'Authorization': 'Bearer Valid'})
        assert response.status_code == 400



    # A valid token and valid config note Id.  The match task will run and succeed.
    # TODO This test is shut off because matcher uses openreview.tools.iterget function which is
    # not provided in the MockORClient that is used by the rest of the matcher to call the openreview-py API.
    #  Because iterget_notes is not a method on an object, its a bit more difficult to refactor the matcher to correctly interface
    # with this API function:  The correct solution would be to create a single OpenReview_API wrapper object that provides
    # all the methods that the matcher calls within the openreview-py library including iterget_notes and then all calls to that library would go through the
    # wrapper.  We could then create a mock subclass of the wrapper and use that in this test.
    @pytest.mark.skip()
    def test_valid_inputs (self):
        # Turn on logging in the web app because these are valid inputs and nothing should
        # go wrong in the app.  If it does, we want to see the errors in the console
        matcher.app.logger.disabled = False
        matcher.app.logger.parent.disabled = False
        response = post_json(self.app, '/match', {'configNoteId': 'ok'},
                             headers={'Authorization': 'Bearer Valid'})
        assert response.status_code == 200

