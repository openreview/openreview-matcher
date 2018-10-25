from matcher import app
import tests.mock_or_client
import openreview
# Wraps the OR Client.  This is necessary because in testing mode we use a mock client and in live mode we
# use the real OR Client.
class Client ():

    def __init__ (self, baseurl = None, username = None, password = None, token= None):
        if app.config['TESTING']:
            self.decorated = tests.mock_or_client.MockORClient(baseurl=baseurl,username=username,password=password,token=token)
        else:
            self.decorated = openreview.Client(baseurl=baseurl,username=username,password=password,token=token)

    def post_note (self, note):
        return self.decorated.post_note(note)

    def get_note(self, note_id):
        return self.decorated.get_note(note_id)

    def get_notes (self, id = None, paperhash = None, forum = None, invitation = None, replyto = None, tauthor = None, signature = None, writer = None, trash = None, number = None, limit = None, offset = None, mintcdate = None, details = None):
        return self.decorated.get_notes(id, paperhash, forum, invitation, replyto, tauthor, signature, writer, trash, number,
                                        limit, offset, mintcdate, details)

    def get_group (self, id):
        return self.decorated.get_group(id)

    def get_invitation (self, id):
        return self.decorated.get_invitation(id)

    def delete_note (self, id):
        return self.decorated.delete_note(id)