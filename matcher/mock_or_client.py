import openreview
from openreview import OpenReviewException
from exc.exceptions import BadTokenException
from matcher.match import Match
from matcher.fields import Configuration

# This is used by the matcher web app to mock the OR-py Client class.  It is set up to throw it's full variety of exceptions
# when given certain test inputs.
class MockORClient (openreview.Client):
    def __init__ (self, baseurl = None, username = None, password = None, token= None, testing=False):
        if token.startswith('Bearer'):
            # just make sure there's two things that result from splitting the Authorization header.
            # It doesn't matter what comes after Bearer.  We'll assume its a working token
            token = token.split()[1]
            if token.upper() != 'VALID':
                raise BadTokenException("The token is invalid")
        else:
            raise BadTokenException("Authorization Bearer XXXX header wasn't passed correctly")



    def post_note (self, note):
        return note

    # produces the relevant failures that might come up for getting a config note and the successful case where it
    # returns an object
    def get_note(self, configNoteId):
        if configNoteId == 'nonExist':
            raise OpenReviewException([{'type': 'Not Found'}])
        elif configNoteId == 'forbidden':
            raise OpenReviewException([{'type': 'Forbidden'}])
        elif configNoteId == 'internal error':
            list = []
            list[2]
        elif configNoteId == 'already_running':
            note = openreview.Note(id='testId',
                                   invitation=None,
                                   readers=[],
                                   writers=[],
                                   signatures=[],
                                   content= {
                                       'title': 'foo',
                                       'metadata_invitation': 1,
                                       'match_group': 1,
                                       'paper_invitation': 1,
                                       'assignment_invitation': 1,
                                       'max_papers': 1,
                                       'max_users': 1,
                                       'min_papers': 1,
                                       'weights': 1,
                                       'constraints': 1,
                                       'scores_names': [],
                                       'scores_weights': [],
                                       'alternates': 3,
                                       'status': Configuration.STATUS_RUNNING
                                   })
            return note
        else:
            note = openreview.Note(id='testId',
                                   invitation=None,
                                   readers=[],
                                   writers=[],
                                   signatures=[],
                                   content= {
                                       'title': 'foo',
                                       'metadata_invitation': 1,
                                       'match_group': 1,
                                       'paper_invitation': 1,
                                       'assignment_invitation': 1,
                                       'max_papers': 1,
                                       'max_users': 1,
                                       'min_papers': 1,
                                       'weights': 1,
                                       'constraints': 1,
                                       'scores_names': [],
                                       'scores_weights': [],
                                       'alternates': 3,
                                       'status': Configuration.STATUS_INITIALIZED
                                   })
            return note


    def get_notes (self, id = None, paperhash = None, forum = None, invitation = None, replyto = None, tauthor = None, signature = None, writer = None, trash = None, number = None, limit = None, offset = None, mintcdate = None, details = None):
        return []

    def get_group (self, id):
        g = {}
        g['id']=id
        return openreview.Group.from_json(g)

    def get_invitation (self, id):
        return openreview.Invitation.from_json({'id': id})

    def delete_note (self, id):
        return {}
