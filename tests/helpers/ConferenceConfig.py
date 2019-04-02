import openreview.tools
import random
import datetime
from matcher.fields import Configuration, PaperReviewerScore, Assignment
from tests.params import Params


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
        self.BID_ID = self.CONF_ID + "/-/Bid"
        self.TPMS_ID = self.CONF_ID + "/-/Tpms"
        self.RECOMMENDATION_ID = self.CONF_ID + "/-/Recommendation"
        self.AFFINITY_ID = self.CONF_ID + "/-/Affinity"


# To see UI for this: http://openreview.localhost/assignments?venue=FakeConferenceForTesting.cc/2019/Conference

class ConferenceConfig:


    def __init__ (self, client, suffix_num, params):

        random.seed(10) # want a reproducible sequence of random numbers
        self.client = client
        self.conf_ids = ConfIds("FakeConferenceForTesting" + str(suffix_num) + ".cc", "2019")
        print("URLS for this conference are like: " + self.conf_ids.CONF_ID)
        self.params = params
        self.config_inv = None
        self.conference = None
        self.paper_notes = []
        self.paper_to_metadata_map = {}
        self.config_note = None
        self.incremental_score = 0.0
        self.build_conference()


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
        self.conference.has_area_chairs(True)
        self.conference.set_area_chairs(emails=[])
        self.reviewers = ["reviewer-" + str(i) + "@acme.com" for i in range(self.params.num_reviewers)]
        self.conference.set_reviewers(emails=self.reviewers)
        self.create_papers()
        # creates three invitations for: metadata, assignment, config AND metadata notes
        self.conference.setup_matching()
        self.build_paper_to_metadata_map()
        self.customize_invitations()
        self.add_reviewer_entries_to_metadata()
        self.create_config_note()

    def customize_invitations (self):
        # replace the default score_names that builder gave with the ones I want
        config_inv = self.client.get_invitation(id=self.get_assignment_configuration_id())
        if config_inv:
            content = config_inv.reply['content']
            del content['scores_names']
            content["scores_names"] = {
                "values-dropdown": self.params.scores_config[Params.SCORE_NAMES_LIST],
                # "values": ['bid', 'recommendation', 'tpms'],
                "required": True,
                "description": "List of scores names",
                "order": 3
            }
            self.client.post_invitation(config_inv)

    def build_paper_to_metadata_map (self):
        for md_note in self.get_metadata_notes():
            self.paper_to_metadata_map[md_note.forum] = md_note

    def gen_score (self, reviewer_ix=0, paper_ix=0):
        if self.params.scores_config[Params.SCORE_TYPE] == Params.RANDOM_SCORE:
            score = random.random()
        elif self.params.scores_config[Params.SCORE_TYPE] == Params.FIXED_SCORE:
            fixed_score = self.params.scores_config[Params.FIXED_SCORE_VALUE]
            score = fixed_score
        elif self.params.scores_config[Params.SCORE_TYPE] == Params.MATRIX_SCORE:
            score = self.params.scores_config[Params.SCORE_MATRIX][reviewer_ix, paper_ix]
        else: #  incremental scores go like 0.1, 0.2, 0.3... to create a discernable pattern we can look for in cost matrix
            self.incremental_score += self.params.scores_config[Params.SCORE_INCREMENT]
            score = self.incremental_score
        return float(score)

    def gen_scores (self, reviewer_ix, paper_ix):
        score_names = self.params.scores_config[Params.SCORE_NAMES_LIST]
        record = {}
        for score_name in score_names:
            record[score_name] = self.gen_score(reviewer_ix, paper_ix)
        return record

    # adds randomly generated scores for reviewers into the papers
    def add_reviewer_entries_to_metadata (self):
        # metadata_notes = self.get_metadata_notes()
        reviewers_group = self.client.get_group(self.conference.get_reviewers_id())
        reviewers = reviewers_group.members
        # iterate through paper notes and then fetch its metadata because order of
        # papers_notes we know, metadata may be in some other order.
        for paper_ix, paper_note in enumerate(self.paper_notes):
            md_note = self.paper_to_metadata_map[paper_note.id]
            entries = []
            for reviewer_ix, reviewer in enumerate(reviewers):
                entry = {PaperReviewerScore.USERID: reviewer,
                         PaperReviewerScore.SCORES: self.gen_scores(reviewer_ix, paper_ix)}
                entries.append(entry)
            md_note.content[PaperReviewerScore.ENTRIES] = entries
            self.client.post_note(md_note)
        self.add_conflicts_to_metadata()

    # params.conflicts_config is dict that maps paper indices to list of user indices that conflict with the paper
    def add_conflicts_to_metadata (self):
        for paper_index, user_index_list in self.params.conflicts_config.items():
            paper_note = self.paper_notes[paper_index]
            forum_id = paper_note.id
            md_note = self.get_metadata_note(forum_id)
            for user_ix in user_index_list:
                reviewer = self.reviewers[user_ix]
                self.add_conflict(md_note, reviewer)
            self.client.post_note(md_note)

    def add_conflict (self, metadata_note, reviewer):
        entry = self.get_user_entry(metadata_note.content[PaperReviewerScore.ENTRIES], reviewer)
        entry[PaperReviewerScore.CONFLICTS] = ['conflict-exists']

    def get_user_entry (self, entry_list, reviewer):
        for entry in entry_list:
            if entry[PaperReviewerScore.USERID] == reviewer:
                return entry
        return None


    def create_papers (self):
        self.paper_notes = []
        for i in range(self.params.num_papers):
            content = {
                'title':  "Paper-" + str(i),
                'authorids': ['jimbob@acme.com']
            }
            paper_note = openreview.Note(**{
                'signatures': ['~Super_User1'],
                'writers': [self.conference.id],
                'readers': [self.conference.id],
                'content': content,
                'invitation': self.conference.get_submission_id()
            })
            posted_submission = self.client.post_note(paper_note)
            self.paper_notes.append(posted_submission)

        print("There are ", len(self.paper_notes), " papers")


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
                'scores_names': self.params.scores_config[Params.SCORE_NAMES_LIST],
                'scores_weights': [1 for n in self.params.scores_config[Params.SCORE_NAMES_LIST]], # each score is weighted 1
                'max_users': str(self.params.num_reviews_needed_per_paper), # max number of reviewers a paper can have
                'min_users': str(self.params.num_reviews_needed_per_paper), # min number of reviewers a paper can have
                'max_papers': str(self.params.reviewer_max_papers), # max number of papers a reviewer can review
                'min_papers': '1', # min number of papers a reviewer can review
                'alternates': '2',
                'constraints': {},
                'custom_loads': {},
                # This seems odd.
                # TODO Question: Shouldn't the config_invitation be CONF_ID/-/Assignment_Configuration
                # 'config_invitation': self.conf_ids.CONFIG_ID,
                'config_invitation': self.conf_ids.CONF_ID,
                # 'paper_invitation': self.conf_ids.SUBMISSION_ID,
                # TODO Question:  The name of the method get_blind_submission_id is misleading
                # because this conference is not using blind papers.   It would be more straightforward if the method
                # was called get_submission_id which would return a blind id if the papers happen to be blind
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

    # out_constraints is added to as: {'forum-id': {"user1" : '-inf' | '+inf', "user2" : ...}   'forum-id2' .... }
    def insert_constraints (self, paper_constraints, out_constraints, val):
        for paper_ix in paper_constraints:
            paper = self.paper_notes[paper_ix]
            if not out_constraints.get(paper.id):
                out_constraints[paper.id] = {}
            for reviewer_ix in paper_constraints[paper_ix]:
                reviewer = self.reviewers[reviewer_ix]
                out_constraints[paper.id][reviewer] = val


    # constraints_config is {'locks' : {0 : [0,2,3], 1 : [4]} Paper 0 locks in users 0,2,3 ; Paper 1 locks in user 4
    #                       {'vetos' : {0 : [1,4], 1 : [5]} Paper 0 vetos users 1,4; Paper 1 vetos user 5
    def add_config_constraints(self):
        constraint_entries = {}
        if not self.params.constraints_config:
            return
        self.insert_constraints(self.params.constraints_vetos, constraint_entries, Configuration.VETO)
        self.insert_constraints(self.params.constraints_locks, constraint_entries, Configuration.LOCK)
        self.config_note.content[Configuration.CONSTRAINTS] = constraint_entries


    def add_config_custom_loads(self):
        if self.params.custom_load_supply_deduction:
            self.set_reviewers_custom_load_to_default()
            self.reduce_reviewers_custom_load_by_shortfall(self.params.custom_load_supply_deduction)
            self.remove_default_custom_loads()


    def set_reviewers_custom_load_to_default (self):
        custom_loads = {}
        default_load = self.params.reviewer_max_papers
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
        default_load = self.params.reviewer_max_papers
        custom_loads = self.config_note.content[Configuration.CUSTOM_LOADS]
        for reviewer in list(custom_loads.keys()):
            if custom_loads[reviewer] == default_load:
                del custom_loads[reviewer]



    @property
    def config_note_id (self):
        return self._config_note_id

    @config_note_id.setter
    def config_note_id (self, config_note_id):
        self._config_note_id = config_note_id

    def get_reviewer (self, index):
        return self.reviewers[index]


    ## Below are routines some of which could go into the matching portion of the conference builder

    def get_paper (self, forum_id):
        for p in self.paper_notes:
            if p.id == forum_id:
                return p
        return None

    def get_metadata_note_entries (self, forum_id):
        md_note = self.get_metadata_note(forum_id)
        if md_note:
            return md_note.content[PaperReviewerScore.ENTRIES]
        else:
            return []

    def get_metadata_note(self, forum_id):
        for note in self.get_metadata_notes():
            if note.forum == forum_id:
                return note
        return None

    def get_metadata_notes_following_paper_order (self):
        res = []
        for p in self.paper_notes:
            res.append(self.paper_to_metadata_map[p.id])
        return res

    def get_metadata_notes (self):
        return list(openreview.tools.iterget_notes(self.client, invitation=self.get_metadata_id()))

    def get_constraints (self):
        return self.config_note.content[Configuration.CONSTRAINTS]

    def get_custom_loads (self):
        return self.config_note.content[Configuration.CUSTOM_LOADS]

    # return papers and their user conflicts as dictionary of forum_ids mapped to lists of users that conflict with the paper.
    def get_conflicts (self):
        res = {}
        for md_note in self.get_metadata_notes():
            forum_id = md_note.forum
            res[forum_id] = []
            for entry in self.get_metadata_note_entries(forum_id):
                if entry.get(PaperReviewerScore.CONFLICTS):
                    res[forum_id].append(entry[PaperReviewerScore.USERID])
        return res


    def get_config_note (self):
        config_note = self.client.get_note(id=self.config_note_id)
        return config_note

    def get_paper_assignment_id (self):
        return self.conference.id + '/-/' + 'Paper_Assignment'

    def get_assignment_configuration_id (self):
        return self.conference.id + '/-/' + 'Assignment_Configuration'

    def get_metadata_id (self):
        return self.conference.id + '/-/' + 'Paper_Metadata'

    def get_paper_notes (self):
        return self.paper_notes

    def get_config_note_status (self):
        config_note = self.get_config_note()
        return config_note.content[Configuration.STATUS]

    def get_assignment_notes (self):
        # return self.conference.get_assignment_notes()   # cannot call this until released
        return self.client.get_notes(invitation=self.get_paper_assignment_id())


    def get_assignment_note(self, forum_id):
        for note in self.get_assignment_notes():
            if note.forum == forum_id:
                return note
        return None

    def get_assignment_note_assigned_reviewers (self, assignment_note):
        return assignment_note.content[Assignment.ASSIGNED_GROUPS]

