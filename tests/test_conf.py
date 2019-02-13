import openreview.tools
import pymongo
import pprint
import random
# Symbols
YR = "2019"
# FakeConferenceForTesting.cc/2019/Conference/-/X
CONF_ID = "FakeConferenceForTesting.cc/" + YR + "/Conference"
PC_ID = CONF_ID + "/Program_Chairs"
AC_ID = CONF_ID + "/Area_Chairs"
REVIEWERS_ID = CONF_ID + "/Reviewers"
SUBMISSION_ID = CONF_ID + "/-/Submission"
INPUT_FILES_DIR = "/home/marshall/iesl/or/scripts/venues/cv-foundation.org/CVPR/2019/Conference/data/"
# This one used to be called REVIEWER_METADATA_ID but I don't like the term "meta-data" for this stuff
PAPER_REVIEWER_SCORE_ID = CONF_ID + "/-/Paper_Reviewer_Scores"
CONFIG_ID = CONF_ID + "/-/Assignment_Configuration"
ASSIGNMENT_ID = CONF_ID + "/-/Paper_Assignment"

# To see UI for this: http://openreview.localhost/assignments?venue=FakeConferenceForTesting.cc/2019/Conference

class TestConf:

    def __init__ (self, client, num_papers=10, num_reviewers=7, conflict_percentage=0.0,
                  paper_min_reviewers=1, reviewer_max_papers=3, custom_load_percentage=0.0,
                  positive_constraint_percentage=0.0, negative_constraint_percentage=0.0):
        self.num_papers = num_papers
        self.num_reviewers = num_reviewers
        self.conflict_percentage = conflict_percentage
        self.custom_load_percentage = custom_load_percentage
        self.positive_constraint_percentage = positive_constraint_percentage
        self.negative_constraint_percentage = negative_constraint_percentage
        self.paper_min_reviewers = paper_min_reviewers
        self.reviewer_max_papers = reviewer_max_papers
        self.submission_inv = None
        self.paper_assignment_inv = None
        self.config_inv = None
        self.paper_reviewer_inv = None

        self.reviewers_group = []
        self.paper_notes = []
        self.paper_reviewer_score_notes = []
        self.config_note = None

        self.set_mongo_client()
        # self.test_db()
        self.clear_previous()
        self.build_conf(client)



    def set_mongo_client (self):
        self.mongo_client = pymongo.MongoClient('localhost', 27017)
        self.db = self.mongo_client.openreview
        self.db_groups = self.db.openreview_groups
        self.db_invitations = self.db.openreview_invitations
        self.db_notes = self.db.openreview_notes

    def test_db (self):
        reviewers = self.db_groups.find_one({"id": REVIEWERS_ID})
        pprint.pprint(reviewers)
        papers = self.db_notes.find({"id": SUBMISSION_ID})
        for p in papers:
            pprint.pprint(p)



    def build_conf (self, client):
        # TODO openreview.builder
        self.create_conf_groups(client)
        self.create_paper_submission_inv(client)
        self.create_assignment_inv(client)
        self.create_config_inv(client)
        self.create_prs_inv(client)

        self.create_reviewers(client)
        self.create_papers(client)
        self.create_prs_notes(client)
        self.create_config_note(client)

    # eliminate db objects created on previous runs of this test-case conference.
    def clear_previous (self):
        res = self.db_groups.delete_one({"id" : REVIEWERS_ID})
        res = self.db_invitations.delete_one({"id" : SUBMISSION_ID})
        res = self.db_invitations.delete_one({"id" : PAPER_REVIEWER_SCORE_ID})
        res = self.db_invitations.delete_one({"id" : CONFIG_ID})
        res = self.db_invitations.delete_one({"id" : ASSIGNMENT_ID})
        res = self.db_notes.delete_many({"invitation" : SUBMISSION_ID})
        res = self.db_notes.delete_many({"invitation" : PAPER_REVIEWER_SCORE_ID})
        res = self.db_notes.delete_many({"invitation" : CONFIG_ID})
        # Delete the assignment notes because the matcher doesn't really do it.
        res = self.db_notes.delete_many({"invitation" : ASSIGNMENT_ID})
        # print("Deleted ", res.deleted_count, " assignment notes")

    def get_config_note_id (self):
        cnote = self.db_notes.find_one({"invitation": CONFIG_ID})
        return cnote['id']

    def get_config_note_status (self):
        cnote = self.db_notes.find_one({"invitation": CONFIG_ID})
        return cnote['content']['status']

    def get_num_assignment_notes (self):
        # anotes = self.db_notes.find({'invitation' : ASSIGNMENT_ID})
        return self.db_notes.count_documents({"invitation": ASSIGNMENT_ID})


    def create_conf_groups (self, client):
        ## User groups

        # post the groups in the conference's path
        groups = openreview.tools.build_groups(CONF_ID)
        for group in groups:
            try:
                existing_group = client.get_group(group.id)
            except openreview.OpenReviewException as e:
                posted_group = client.post_group(group)
                print(posted_group.id)

        # Create groups for PCs, ACs, and reviewers
        # N.B. The groups for the conference are included in the list.  The newly created group is last in the list
        pcs_group = openreview.tools.build_groups(PC_ID)[-1] # last one in list is the PC group
        acs_group = openreview.tools.build_groups(AC_ID)[-1] # AC group is last
        self.reviewers_group = openreview.tools.build_groups(REVIEWERS_ID)[-1] # reviewers group is last
        client.post_group(pcs_group)
        client.post_group(acs_group)
        client.post_group(self.reviewers_group)
        pcs_group = client.get_group(PC_ID)
        acs_group = client.get_group(AC_ID)
        # self.reviewers_group = client.get_group(REVIEWERS_ID)

        # Global group definitions
        conference = openreview.Group(**{
            'id': CONF_ID,
            'readers':['everyone'],
            'writers': [CONF_ID],
            'signatures': [],
            'signatories': [CONF_ID],
            'members': [],
            # 'web': os.path.abspath('../webfield/homepage.js')
        })
        client.post_group(conference)

    def create_paper_submission_inv (self, client):
        SUBMISSION_DEADLINE = openreview.tools.timestamp_GMT(year=2019, month=9, day=1)

        self.submission_inv = openreview.Invitation(
            id = SUBMISSION_ID,
            duedate = SUBMISSION_DEADLINE,
            readers = ['everyone'],
            signatures = [CONF_ID],
            writers = [CONF_ID],
            invitees = [],
            reply = {
                'readers': {
                    'values': [
                        CONF_ID
                    ]
                },
                'signatures': { 'values': [CONF_ID]
                                },
                'writers': {
                    'values': [CONF_ID]
                },
                'content': {
                    'title': {'value-regex': '.*'},
                    'number': {'value-regex': '.*'}
                }
            }
        )
        inv = client.post_invitation(self.submission_inv)



    def create_reviewers (self, client):
        # Add members to the reviewers group
        self.reviewers_group.members = ["reviewer-" + str(i) + "@acme.com" for i in range(self.num_reviewers)]
        print("There are ", len(self.reviewers_group.members), " reviewers")
        client.post_group(self.reviewers_group)

    def create_papers (self, client):
        paper_note_ids = []
        for i in range(self.num_papers):
            content = {
                'title':  "Paper-" + str(i),
                'number': i,
            }
            posted_submission = client.post_note(openreview.Note(**{
                'signatures': [CONF_ID],
                'writers': [CONF_ID],
                'readers': [CONF_ID],
                'content': content,
                'invitation': SUBMISSION_ID
            }))
            paper_note_ids.append(posted_submission.id)
        self.paper_notes = list(openreview.tools.iterget_notes(client, invitation=SUBMISSION_ID))
        print("There are ", len(self.paper_notes), " papers")

    def create_prs_inv (self, client):
        # Create the invitation for the Paper-Reviewer_Scores note (used to be called meta-data)
        inv = openreview.Invitation(
            id = PAPER_REVIEWER_SCORE_ID,
            readers = ['everyone'],
            signatures = [CONF_ID],
            writers = [CONF_ID],
            invitees = [],
            reply = {
                'forum': None,
                'replyto': None,
                'readers': { 'values': [CONF_ID ]
                             },
                'signatures': { 'values': [CONF_ID]
                                },
                'writers': { 'values': [CONF_ID]
                             },
                'content': {  }
            }
        )
        self.paper_reviewer_inv = client.post_invitation(inv)


    def create_prs_notes (self, client):
        random.seed(10) # want a reproducible sequence
        self.paper_reviewer_score_notes = []

        for paper_note in self.paper_notes:
            entries = []
            # Create a list of entries for each user.  Each entry has scores.
            for reviewer in self.reviewers_group.members:
                entry = {'userid': reviewer,
                         'scores': {'tpms': random.random(), 'recommendation': random.random() }}

                # conflicts for a paper go into the user record as a non-None value to disable this user from reviewer this paper
                if random.random() < self.conflict_percentage:
                    entry['conflicts'] = ['conflict']
                entries.append(entry)

            note = openreview.Note(forum=paper_note.id,
                                   replyto=paper_note.id,
                                   invitation=PAPER_REVIEWER_SCORE_ID,
                                   readers=[CONF_ID],
                                   writers=[CONF_ID],
                                   signatures=[CONF_ID],
                                   content={'entries': entries})
            client.post_note(note)
            self.paper_reviewer_score_notes.append(note)

    def create_assignment_inv (self, client):
        self.paper_assignment_inv = openreview.Invitation(
            id = ASSIGNMENT_ID,
            readers = [CONF_ID],
            signatures = [CONF_ID],
            writers = [CONF_ID],
            invitees = [],
            reply = {
                'forum': None,
                'replyto': None,
                'readers': { 'values': [CONF_ID ]
                             },
                'signatures': { 'values': [CONF_ID]
                                },
                'writers': { 'values': [CONF_ID]
                             },
                'content': {}
            }
        )
        client.post_invitation(self.paper_assignment_inv)

    def create_config_inv (self, client):
        self.config_inv = openreview.Invitation(
            id = CONFIG_ID,
            readers = ['everyone'],
            signatures = [CONF_ID],
            writers = [CONF_ID],
            invitees = [],
            reply = {
                'forum': None,
                'replyto': None,
                'readers': { 'values': [CONF_ID ]
                             },
                'signatures': { 'values': [CONF_ID]
                                },
                'writers': { 'values': [CONF_ID]
                             },
                'content': {
                    "title": {
                        "value-regex": ".{1,250}",
                        "required": True,
                        "description": "Title of the configuration.",
                        "order": 1
                    },
                    "max_users": {
                        "value-regex": "[0-9]+",
                        "required": True,
                        "description": "Max number of reviewers that can review a paper",
                        "order": 2
                    },
                    "min_users": {
                        "value-regex": "[0-9]+",
                        "required": True,
                        "description": "Min number of reviewers required to review a paper",
                        "order": 3
                    },
                    "max_papers": {
                        "value-regex": "[0-9]+",
                        "required": True,
                        "description": "Max number of reviews a person has to do",
                        "order": 4
                    },
                    "min_papers": {
                        "value-regex": "[0-9]+",
                        "required": True,
                        "description": "Min number of reviews a person should do",
                        "order": 5
                    },
                    "alternates": {
                        "value-regex": "[0-9]+",
                        "required": True,
                        "description": "Number of alternate reviewers for a paper",
                        "order": 6
                    },
                    "config_invitation": {
                        "value": CONFIG_ID,
                        "required": True,
                        "description": "Invitation to get the configuration note",
                        "order": 3
                    },
                    "scores_names": {
                        # "values-dropdown": ['bid', 'recommendation', 'tpms'],
                        "values": ['bid', 'recommendation', 'tpms'],
                        "required": True,
                        "description": "List of scores names",
                        "order": 3
                    },
                    "scores_weights": {
                        # "values-regex": "\\d*\\.?\\d*",
                        "values": ['1','2','3'],
                        "required": True,
                        "description": "Comma separated values of scores weights, should follow the same order than scores_names",
                        "order": 3
                    },
                    "status": {
                        "value-dropdown": ['Initialized', 'Running', 'Error', 'No Solution', 'Complete', 'Deployed']
                    },
                    "custom_loads" : {
                        "value-dict": {},
                        "required": False,
                        "description": "Manually entered custom user maximun loads",
                        "order": 8
                    },
                    "constraints": {
                        "value-dict": {},
                        "required": False,
                        "description": "Manually entered user/papers constraints",
                        "order": 9
                    },
                    'paper_invitation': {"value": SUBMISSION_ID,
                                         "required": True,
                                         "description": "Invitation to get the configuration note",
                                         "order": 8
                                         },
                    'metadata_invitation': {"value": PAPER_REVIEWER_SCORE_ID,
                                            "required": True,
                                            "description": "Invitation to get the configuration note",
                                            "order": 9
                                            },
                    'assignment_invitation': {"value": ASSIGNMENT_ID,
                                              "required": True,
                                              "description": "Invitation to get the configuration note",
                                              "order": 10
                                              },
                    'match_group': {"value": REVIEWERS_ID,
                                    "required": True,
                                    "description": "Invitation to get the configuration note",
                                    "order": 11
                                    }

                }
            }
        )
        client.post_invitation(self.config_inv)

    def create_config_note (self, client):
        self.config_note = client.post_note(openreview.Note(**{
            'invitation': CONFIG_ID,
            'readers': [CONF_ID],
            'writers': [CONF_ID],
            'signatures': [CONF_ID],
            'content': {
                'title': 'reviewers',
                'scores_names': ['bid','recommendation', 'tpms'],
                'scores_weights': ['1', '2', '3'],
                'max_users': str(self.paper_min_reviewers), # max number of reviewers a paper can have
                'min_users': str(self.paper_min_reviewers), # min number of reviewers a paper can have
                'max_papers': str(self.reviewer_max_papers), # max number of papers a reviewer can review
                'min_papers': '1', # min number of papers a reviewer can review
                'alternates': '2',
                'constraints': {},
                'custom_loads': {},
                "config_invitation": CONFIG_ID,
                'paper_invitation': SUBMISSION_ID,
                'metadata_invitation': PAPER_REVIEWER_SCORE_ID,
                'assignment_invitation': ASSIGNMENT_ID,
                'match_group': REVIEWERS_ID,
                'status': 'Initialized'
            }
        }))
        # custom_loads go into config.content as custom_loads: {"user-name": load ...}
        custom_loads = {}

        self.total_review_supply = 0
        for rev in self.reviewers_group.members:
            if random.random() < self.custom_load_percentage:
                reviewer_max_load = random.randint(1,self.reviewer_max_papers)
                self.total_review_supply += reviewer_max_load
                custom_loads[rev] = reviewer_max_load
            else:
                self.total_review_supply += self.reviewer_max_papers
        self.config_note.content['custom_loads'] = custom_loads

        # constraints go into config.content as constraints: {'forum-id': {"user1" : '-inf' | '+inf', "user2" : ...}   'forum-id2' .... }
        constraints = {}
        # TODO seems like constraints should be in PRS notes since they apply to a paper
        for n in self.paper_notes:
            paper_id = n.id
            user_map = {}
            for r in self.reviewers_group.members:
                if random.random() < self.positive_constraint_percentage:
                    user_map[r] = '+inf'
                elif random.random() < self.negative_constraint_percentage:
                    user_map[r] = '-inf'
            constraints[paper_id] = user_map
        self.config_note.content['constraints'] = constraints
        client.post_note(self.config_note)

    def get_total_review_supply (self):
        return self.total_review_supply



if __name__ == '__main__':
    tc = TestConf(None,4,4)
