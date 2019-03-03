import openreview.tools
import random
import datetime
from fields import Configuration

# Symbols

class Params:
    NUM_PAPERS = 'num_papers'
    NUM_REVIEWERS = 'num_reviewers'
    NUM_REVIEWS_NEEDED_PER_PAPER = 'reviews_needed_per_paper'
    REVIEWER_MAX_PAPERS = 'reviewer_max_papers'
    CUSTOM_LOAD_CONFIG = 'custom_load_config'
    CUSTOM_LOAD_SUPPLY_DEDUCTION = 'supply_deduction'
    THEORETICAL_SUPPLY = 'theoretical_supply'
    ACTUAL_SUPPLY = 'actual_supply'
    DEMAND = 'demand'



# This one used to be called REVIEWER_METADATA_ID but I don't like the term "meta-data" for this stuff

class ConfIds:

    # name should be like: FakeConferenceForTesting3.cc
    def __init__ (self, conf_name, year):
        self.CONF_ID = conf_name + "/" + year + "/Conference"
        self.PROGRAM_CHAIRS_ID = self.CONF_ID + "/Program_Chairs"
        self.AC_ID = self.CONF_ID + "/Area_Chairs"
        self.REVIEWERS_ID = self.CONF_ID + "/Reviewers"
        self.SUBMISSION_ID = self.CONF_ID + "/-/Submission"
        self.BLIND_SUBMISSION_ID = self.CONF_ID + "/-/Blind_Submission"
        self.METADATA_INV_ID = self.CONF_ID + '/-/Paper_Metadata'
        self.CONFIG_ID = self.CONF_ID + "/-/Assignment_Configuration"
        self.ASSIGNMENT_ID = self.CONF_ID + "/-/Paper_Assignment"


# To see UI for this: http://openreview.localhost/assignments?venue=FakeConferenceForTesting.cc/2019/Conference

class ConferenceConfig:


    def __init__ (self, client, suffix_num, params):

        '''
        num=0, num_papers=10, num_reviewers=7, conflict_percentage=0.0,
                  paper_min_reviewers=1, reviewer_max_papers=3, custom_load_percentage=0.0,
                  positive_constraint_percentage=0.0, negative_constraint_percentage=0.0, custom_load_config={}):
        '''

        self.client = client
        self.conf_ids = ConfIds("FakeConferenceForTesting" + str(suffix_num) + ".cc", "2019")
        print("URLS for this conference are like: " + self.conf_ids.CONF_ID)
        self.num_papers = params[Params.NUM_PAPERS]
        self.num_reviewers = params[Params.NUM_REVIEWERS]
        self.conflict_percentage = 0.0
        self.custom_load_config = params.get(Params.CUSTOM_LOAD_CONFIG)
        self.positive_constraint_percentage = 0.0
        self.negative_constraint_percentage = 0.0
        self.paper_min_reviewers = params[Params.NUM_REVIEWS_NEEDED_PER_PAPER]
        self.reviewer_max_papers = params[Params.REVIEWER_MAX_PAPERS]
        self.submission_inv = None
        self.paper_assignment_inv = None
        self.config_inv = None
        self.paper_reviewer_inv = None

        self.conference = None

        self.reviewers_group = []
        self.paper_notes = []
        self.paper_reviewer_score_notes = []
        self.config_note = None
        self.config_note_id = None

        self.build_conference()

    ## Below are proposed API routines that should go into the matching portion of the conference builder

    def get_paper_assignment_id (self):
        return self.conference.id + '/-/' + 'Paper_Assignment'

    def get_assignment_configuration_id (self):
        return self.conference.id + '/-/' + 'Assignment_Configuration'

    def get_metadata_id (self):
        return self.conference.id + '/-/' + 'Paper_Metadata'



    def build_conference (self):
        builder = openreview.conference.ConferenceBuilder(self.client)
        builder.set_conference_id(self.conf_ids.CONF_ID)
        builder.set_conference_name('Conference for Integration Testing')
        builder.set_conference_short_name('Integration Test')
        self.conference = builder.get_result()
        self.conference.open_submissions(due_date = datetime.datetime(2019, 3, 25, 23, 59),
                                    remove_fields=['authors', 'abstract', 'pdf', 'keywords', 'TL;DR'])
        self.conf_ids.SUBMISSION_ID = self.conference.get_submission_id()
        self.conference.set_program_chairs(emails=[])
        self.conference.set_area_chairs(emails=[])
        self.reviewers = ["reviewer-" + str(i) + "@acme.com" for i in range(self.num_reviewers)]
        self.conference.set_reviewers(emails=self.reviewers)
        self.create_papers()
        # creates three invitations for: metadata, assignment, config AND metadata notes
        # TODO:  The config invitation only includes bid as a possible score and I need to
        # have it include recommendation and tpms.   No way to tell builder what I want, so seems I need to modify
        # resulting invitation to have what I need
        # TODO:  Question:  Should I be deleting the scores_names from the content of the invitation and
        # replacing with what I want (like I do in customize_invitations)?
        self.conference.setup_matching()
        self.customize_invitations()
        self.add_reviewer_entries_to_metadata()

        # TODO metadata notes created above need to have entries for each user for scores and conflicts
        # TODO: Question: I see warnings from builder saying that metadata not being built for members without
        # profiles.   Shouldn't I be allowed to create metadata for simple email users? (e.g. like CVPR)
        self.add_scores_and_conflicts_to_metadata()
        self.create_config_note()

    def customize_invitations (self):
        # replace the default score_names that builder gave with the ones I want
        config_inv = self.client.get_invitation(id=self.get_assignment_configuration_id())
        if config_inv:
            content = config_inv.reply['content']
            del content['scores_names']
            content["scores_names"] = {
                "values-dropdown": ['bid', 'recommendation', 'tpms'],
                # "values": ['bid', 'recommendation', 'tpms'],
                "required": True,
                "description": "List of scores names",
                "order": 3
                }
            self.client.post_invitation(config_inv)

    # conference builder does not add entries into each metadata note; one for each reviewer
    # TODO this is where conflicts also go.
    def add_reviewer_entries_to_metadata (self):
        metadata_notes = list(openreview.tools.iterget_notes(self.client, invitation=self.get_metadata_id()))
        reviewers_group = self.client.get_group(self.conference.get_reviewers_id())
        reviewers = reviewers_group.members
        for md_note in metadata_notes:
            entries = []
            for reviewer in reviewers:
                entry = {'userid': reviewer,
                         'scores': {'tpms': random.random(), 'recommendation': random.random() }}
                entries.append(entry)
            md_note.content['entries'] = entries
            self.client.post_note(md_note)





    def create_papers (self):
        paper_note_ids = []
        for i in range(self.num_papers):
            # TODO jimbob might need to become a legit user and not just an email
            content = {
                'title':  "Paper-" + str(i),
                'authorids': ['jimbob@acme.com']
            }
            posted_submission = self.client.post_note(openreview.Note(**{
                'signatures': ['~Super_User1'],
                'writers': [self.conference.id],
                'readers': [self.conference.id],
                'content': content,
                'invitation': self.conference.get_submission_id()
            }))
            paper_note_ids.append(posted_submission.id)

        self.paper_notes = list(openreview.tools.iterget_notes(self.client, invitation=self.conference.get_submission_id()))
        print("There are ", len(self.paper_notes), " papers")



    def add_scores_and_conflicts_to_metadata (self):
        pass

    #TODO integrate entries created here into the metadata notes built by builder
    def create_metadata_notes (self):
        random.seed(10) # want a reproducible sequence
        self.paper_reviewer_score_notes = []

        for paper_note in self.paper_notes:
            entries = self.create_all_reviewer_entries()
            note = openreview.Note(forum=paper_note.id,
                                   replyto=paper_note.id,
                                   invitation=self.conf_ids.PAPER_REVIEWER_SCORE_ID,
                                   readers=[self.conf_ids.CONF_ID],
                                   writers=[self.conf_ids.CONF_ID],
                                   signatures=[self.conf_ids.CONF_ID],
                                   content={'entries': entries})
            self.client.post_note(note)
            self.paper_reviewer_score_notes.append(note)

    def create_all_reviewer_entries(self):
        entries = []
        # Create a list of entries for each user.  Each entry has scores.
        for reviewer in self.reviewers:
            entry = {'userid': reviewer,
                     'scores': {'tpms': random.random(), 'recommendation': random.random()}}

            # conflicts for a paper go into the user record as a non-None value to disable this user from reviewer this paper
            if random.random() < self.conflict_percentage:
                entry['conflicts'] = ['conflict']
            entries.append(entry)
        return entries



    def create_config_inv (self):
        self.config_inv = openreview.Invitation(
            id = self.conf_ids.CONFIG_ID,
            readers = ['everyone'],
            signatures = [self.conf_ids.CONF_ID],
            writers = [self.conf_ids.CONF_ID],
            invitees = [],
            reply = {
                'forum': None,
                'replyto': None,
                'readers': { 'values': [self.conf_ids.CONF_ID ]
                             },
                'signatures': { 'values': [self.conf_ids.CONF_ID]
                                },
                'writers': { 'values': [self.conf_ids.CONF_ID]
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
                        "value": self.conf_ids.CONFIG_ID,
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
                    'paper_invitation': {"value": self.conf_ids.SUBMISSION_ID,
                                         "required": True,
                                         "description": "Invitation to get the configuration note",
                                         "order": 8
                                         },
                    'metadata_invitation': {"value": self.conf_ids.PAPER_REVIEWER_SCORE_ID,
                                            "required": True,
                                            "description": "Invitation to get the configuration note",
                                            "order": 9
                                            },
                    'assignment_invitation': {"value": self.conf_ids.ASSIGNMENT_ID,
                                              "required": True,
                                              "description": "Invitation to get the configuration note",
                                              "order": 10
                                              },
                    'match_group': {"value": self.conf_ids.REVIEWERS_ID,
                                    "required": True,
                                    "description": "Invitation to get the configuration note",
                                    "order": 11
                                    }

                }
            }
        )
        self.client.post_invitation(self.config_inv)

    def create_config_note (self):
        self.config_note = self.client.post_note(openreview.Note(**{
            'invitation': self.get_assignment_configuration_id(),
            # TODO Question: Had to change because invitation wants conf_id and program_chairs.  Is this always the way readers should be?
            # 'readers': [self.conference.id],
            'readers': [self.conference.id, self.conference.get_program_chairs_id()],
            # TODO Question: Similar to above with writers
            'writers': [self.conference.id, self.conference.get_program_chairs_id()],
            # TODO Question: Had to change because invitation wants it to be program_chairs.  Is this always the way signatures should be?
            # 'signatures': [self.conference.id],
            'signatures': [self.conference.get_program_chairs_id()],
            'content': {
                'title': 'reviewers',
                # TODO Question:  Can only set these because I customized the invitation
                'scores_names': ['bid','recommendation', 'tpms'],
                'scores_weights': ['1', '2', '3'],
                'max_users': str(self.paper_min_reviewers), # max number of reviewers a paper can have
                'min_users': str(self.paper_min_reviewers), # min number of reviewers a paper can have
                'max_papers': str(self.reviewer_max_papers), # max number of papers a reviewer can review
                'min_papers': '1', # min number of papers a reviewer can review
                'alternates': '2',
                'constraints': {},
                'custom_loads': {},
                # This seems odd.
                # TODO Question: Shouldn't the config_invitation be CONF_ID/-/Assignment_Configuration
                # 'config_invitation': self.conf_ids.CONFIG_ID,
                'config_invitation': self.conf_ids.CONF_ID,
                # 'paper_invitation': self.conf_ids.SUBMISSION_ID,
                # TODO Question:  When I built conference, it builds the paper invitation with a regular submission Id
                # Not sure when to use Blind vs regular.  Can builder return to caller the correct submission id to use
                # 1.  What should be set on the invitation of a paper?  2. What should be set here?
                'paper_invitation': self.conference.get_blind_submission_id(),
                'metadata_invitation': self.get_metadata_id(),
                'assignment_invitation': self.get_paper_assignment_id(),
                'match_group': self.conference.get_reviewers_id(),
                'status': 'Initialized'
            }
        }))
        self.add_config_custom_loads()
        self.add_config_constraints()
        self.config_note = self.client.post_note(self.config_note)
        self._config_note_id = self.config_note.id

    def add_config_constraints(self):
        # constraints go into config.content as constraints: {'forum-id': {"user1" : '-inf' | '+inf', "user2" : ...}   'forum-id2' .... }
        constraints = {}
        for n in self.paper_notes:
            paper_id = n.id
            user_map = {}
            for r in self.reviewers:
                if random.random() < self.positive_constraint_percentage:
                    user_map[r] = '+inf'
                elif random.random() < self.negative_constraint_percentage:
                    user_map[r] = '-inf'
            constraints[paper_id] = user_map
        self.config_note.content['constraints'] = constraints

    def add_config_custom_loads(self):
        if self.custom_load_config and self.custom_load_config.get(Params.CUSTOM_LOAD_SUPPLY_DEDUCTION):
            self.set_reviewers_custom_load_to_default()
            self.reduce_reviewers_custom_load_by_shortfall(self.custom_load_config[Params.CUSTOM_LOAD_SUPPLY_DEDUCTION])
            self.remove_default_custom_loads()


    def set_reviewers_custom_load_to_default (self):
        custom_loads = {}
        default_load = self.reviewer_max_papers
        for rev in self.reviewers:
            custom_loads[rev] = default_load
        self.config_note.content[Configuration.CUSTOM_LOADS] = custom_loads

    # cycle through the reviewers reducing their load until supply deduction has been reached
    def reduce_reviewers_custom_load_by_shortfall (self, supply_deduction):
        custom_loads = self.config_note.content[Configuration.CUSTOM_LOADS]
        while supply_deduction > 0:
            for rev in custom_loads:
                if supply_deduction > 0:
                    custom_loads[rev] -= 1
                    supply_deduction -= 1
                else:
                    return

    # any custom_loads that are just default load should be removed so that we only test ones that actually reduce the supply.
    def remove_default_custom_loads (self):
        default_load = self.reviewer_max_papers
        custom_loads = self.config_note.content[Configuration.CUSTOM_LOADS]
        for reviewer in list(custom_loads.keys()):
            if custom_loads[reviewer] == default_load:
                del custom_loads[reviewer]

    def get_custom_loads (self):
        return self.config_note.content[Configuration.CUSTOM_LOADS]

    def get_total_review_supply (self):
        return self.total_review_supply


    def get_config_note (self):
        config_note = self.client.get_note(id=self.config_note_id)
        return config_note

    @property
    def config_note_id (self):
        return self._config_note_id

    @config_note_id.setter
    def config_note_id (self, config_note_id):
        self._config_note_id = config_note_id

    def get_config_note_status (self):
        config_note = self.get_config_note()
        return config_note.content['status']

    def get_assignment_notes (self):
        # return self.conference.get_assignment_notes()   # cannot call this until released
        return self.client.get_notes(invitation=self.get_paper_assignment_id())

    def get_num_assignment_notes (self):
        return len(self.client.get_notes(invitation=self.get_paper_assignment_id()))


if __name__ == '__main__':
    tc = ConferenceConfig(None, 4, 4)
