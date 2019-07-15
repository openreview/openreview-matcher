import openreview.tools
import random
import time
import datetime
import openreview
from collections import defaultdict
from itertools import cycle
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
from openreview import Edge, Invitation
from matcher.fields import Configuration, PaperReviewerScore, Assignment
from helpers.Params import Params


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
        self.AGGREGATE_SCORE_ID = self.CONF_ID + "/-/Aggregate_Score"
        self.CUSTOM_LOAD_INV_ID = self.CONF_ID + "/-/Custom_Load"
        # self.CONSTRAINTS_INV_ID = self.CONF_ID + "/-/Constraints"
        self.CONFLICTS_INV_ID = self.CONF_ID + "/-/Conflicts"



# To see UI for this: http://openreview.localhost/assignments?venue=FakeConferenceForTesting.cc/2019/Conference

class ConferenceConfig:


    def __init__ (self, client, suffix_num, params):

        random.seed(10) # want a reproducible sequence of random numbers
        self._score_invitations = []
        self._silence = True
        self.client = client
        self.config_title = 'Reviewers'
        self.conf_ids = ConfIds("FakeConferenceForTesting" + str(suffix_num), "2019")
        if not self._silence:
            print("URLS for this conference are like: " + self.conf_ids.CONF_ID)
        self.params = params
        self.config_inv = None
        self.conference = None
        self.score_names = None
        self.paper_notes = []
        self.paper_to_metadata_map = {}
        self.config_note = None
        self.incremental_score = 0.0
        self.build_conference()

    @property
    def silence (self):
        return self._silence

    @silence.setter
    def silence (self, silence):
        self._silence= silence

    @property
    def score_invitation_ids (self):
        return [inv.id for inv in self.score_invitations]

    @property
    def score_invitations (self):
        return self._score_invitations

    @property
    def config_note_id (self):
        return self._config_note_id

    @config_note_id.setter
    def config_note_id (self, config_note_id):
        self._config_note_id = config_note_id


    def build_conference (self):
        builder = openreview.conference.ConferenceBuilder(self.client)
        builder.set_conference_id(self.conf_ids.CONF_ID)
        print("Building conference "+ self.conf_ids.CONF_ID)
        builder.set_conference_name('Conference for Integration Testing')
        builder.set_conference_short_name('Integration Test')
        builder.has_area_chairs(True)
        builder.set_submission_stage(due_date = datetime.datetime(2019, 3, 25, 23, 59), remove_fields=['authors', 'abstract', 'pdf', 'keywords', 'TL;DR'])
        self.conference = builder.get_result()
        self.conf_ids.SUBMISSION_ID = self.conference.get_submission_id()
        self.conference.set_program_chairs(emails=[])
        self.conference.set_area_chairs(emails=[])
        self.reviewers = ["reviewer-" + str(i) + "@acme.com" for i in range(self.params.num_reviewers)]
        self.conference.set_reviewers(emails=self.reviewers)
        self.create_papers()
        # creates invitations
        self.conference.setup_matching()
        self.score_names = [PaperReviewerEdgeInvitationIds.get_score_name_from_invitation_id(inv_id) for inv_id in self.params.scores_config[Params.SCORES_SPEC].keys()]

        self.customize_invitations()
        self.add_score_edges()
        self.add_conflict_edges()
        self.config_note = self.create_and_post_config_note()



    # The score_specification inside the params is like {'affinity': {'weight': 1, 'default': 0} ...}.   This will replace the
    # dict with one that has keys which are score_edge_invitation_ids (e.g. FakeConference/2019/Conference/-/affinity)
    def update_score_spec (self):
        scores_spec = self.params.scores_config[Params.SCORES_SPEC]
        fixed_key_spec = {self.conf_ids.CONF_ID + '/-/' + k : v for k, v in scores_spec.items()}
        self.params.scores_config[Params.SCORES_SPEC] = fixed_key_spec

    def build_score_invitations (self):
        '''
        build only the invitations for the scores specified in the configuration parameters.  Also builds a score_invitation
        '''
        # score_names = self.params.scores_config[Params.SCORE_NAMES_LIST]
        score_edge_inv_id = self.params.scores_config[Params.SCORES_SPEC].keys()
        for inv_id in score_edge_inv_id:
            inv = Invitation(id = inv_id,
                             readers = ['everyone'],
                             invitees = ['everyone'],
                             writers = [self.conf_ids.CONF_ID],
                             signatures = [self.conf_ids.CONF_ID],
                             reply = {
                                 'readers': {
                                     'values': [self.conf_ids.CONF_ID]
                                 },
                                 'writers': {
                                     'values': [self.conf_ids.CONF_ID]
                                 },
                                 'signatures': {
                                     'values': [self.conf_ids.CONF_ID]
                                 },
                                 'content': {
                                     'head': {
                                         'type': 'Note',
                                     },
                                     'tail': {
                                         'type': 'Group'
                                     },
                                     'label': {
                                         'value-regex': '.*'
                                     },
                                     'weight': {
                                         'value-regex': '.*'
                                     }
                                 }
                             })
            inv = self.client.post_invitation(inv)
            self._score_invitations.append(inv)

    def customize_invitations (self):
        self.customize_config_invitation()

    def customize_config_invitation (self):
        self.update_score_spec()
        self.build_score_invitations()

    def gen_score (self, score_name, reviewer_ix=0, paper_ix=0):
        if self.params.scores_config[Params.SCORE_TYPE] == Params.RANDOM_SCORE:
            score = random.random()
        elif self.params.scores_config[Params.SCORE_TYPE] == Params.RANDOM_CHOICE_SCORE:
            score = random.choice(self.params.scores_config[Params.SCORE_CHOICES])
        elif self.params.scores_config[Params.SCORE_TYPE] == Params.FIXED_SCORE:
            fixed_score_or_scores = self.params.scores_config[Params.FIXED_SCORE_VALUE]
            fixed_score = fixed_score_or_scores[score_name] if isinstance(fixed_score_or_scores, dict) else fixed_score_or_scores
            score = fixed_score
        elif self.params.scores_config[Params.SCORE_TYPE] == Params.MATRIX_SCORE:
            # Extended to allow storing a dict of matrices where a score_name maps to each matrix
            matrix_or_matrices = self.params.scores_config[Params.SCORE_MATRIX]
            matrix = matrix_or_matrices[score_name] if type(matrix_or_matrices) == dict else matrix_or_matrices
            score = matrix[reviewer_ix, paper_ix]
        else: #  incremental scores go like 0.1, 0.2, 0.3... to create a discernable pattern we can look for in cost matrix
            self.incremental_score += self.params.scores_config[Params.SCORE_INCREMENT]
            score = self.incremental_score
        return score

    def gen_scores (self, reviewer_ix, paper_ix):
        score_names = self.score_names
        record = {}
        for score_name in score_names:
            record[score_name] = self.gen_score(score_name, reviewer_ix, paper_ix)
        return record

    def add_score_edges (self):
        if not self._silence:
            print("Starting to build score edges")
        now = time.time()
        # create the invitations for the score edges now that other parts of the conference have been built
        # self.build_score_invitations()
        paper_notes = self.get_paper_notes()
        reviewers_group = self.client.get_group(self.conference.get_reviewers_id())
        reviewers = reviewers_group.members
        edge_type_dict = defaultdict(list) # maps edge_inv_ids to a list of edges of that invitation / so that post_bulk won't complain
        paper_ix = 0
        for paper_note in paper_notes:
            reviewer_ix = 0
            for reviewer in reviewers:
                for score_inv in self.score_invitations:
                    score_name = PaperReviewerEdgeInvitationIds.get_score_name_from_invitation_id(score_inv.id)
                    score = self.gen_score(score_name, reviewer_ix=reviewer_ix, paper_ix=paper_ix )
                    if (score == 0 or score == '0') and self.params.scores_config.get(Params.OMIT_ZERO_SCORE_EDGES, False):
                        pass
                    elif isinstance(score, str):
                        edge = Edge(head=paper_note.id, tail=reviewer, label=score, weight=0, invitation=score_inv.id, readers=[self.conf_ids.CONF_ID], writers=[self.conf_ids.CONF_ID], signatures=[self.conf_ids.CONF_ID])
                        edge_type_dict[score_inv.id].append(edge)
                    else:
                        edge = Edge(head=paper_note.id, tail=reviewer, weight=float(score), invitation=score_inv.id, readers=[self.conf_ids.CONF_ID], writers=[self.conf_ids.CONF_ID], signatures=[self.conf_ids.CONF_ID])
                        edge_type_dict[score_inv.id].append(edge)

                reviewer_ix += 1
            paper_ix += 1
        for score_edges in edge_type_dict.values():
            openreview.tools.post_bulk_edges(self.client, score_edges)

        if not self._silence:
            print("Time to build score edges: ", time.time() - now)


    # Not sure if the conference builder does this automatically from the papers and reviewers
    def add_conflict_edges(self):
        edges = []
        for paper_index, user_index_list in self.params.conflicts_config.items():
            paper_note = self.paper_notes[paper_index]
            for user_ix in user_index_list:
                reviewer = self.reviewers[user_ix]
                edge = Edge(head=paper_note.id, tail=reviewer, invitation=self.conf_ids.CONFLICTS_INV_ID, weight=1,
                            label='domain.com', readers=[self.conf_ids.CONF_ID], writers=[self.conf_ids.CONF_ID], signatures=[self.conf_ids.CONF_ID])
                edges.append(edge)
        openreview.tools.post_bulk_edges(self.client, edges)



    def create_papers (self):
        self.paper_notes = []
        for i in range(self.params.num_papers):
            content = {
                'title':  "Paper-" + str(i),
                'authorids': ['jimbob@test.com']
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
        if not self._silence:
            print("There are ", len(self.paper_notes), " papers")


    def create_and_post_config_note (self):
        self.create_config_note() # override in the subclass adds in other fields before posting can be done
        self.post_config_note()

    def create_config_note (self):
        '''
        creates a config note but does not post it so that the sublcass override method can add additional stuff before posting happens.
        :return:
        '''
        self.config_note = openreview.Note(**{
            'invitation': self.get_assignment_configuration_id(),
            'readers': [self.conference.id],
            'writers': [self.conference.id,],
            'signatures': [self.conference.id],
            'content': {
                'title': self.config_title,
                Configuration.SCORES_SPECIFICATION : self.params.scores_config[Params.SCORES_SPEC],
                'max_users': str(self.params.num_reviews_needed_per_paper), # max number of reviewers a paper can have
                'min_users': str(self.params.num_reviews_needed_per_paper), # min number of reviewers a paper can have
                'max_papers': str(self.params.reviewer_max_papers), # max number of papers a reviewer can review
                'min_papers': '1', # min number of papers a reviewer can review
                'alternates': str(self.params.alternates), # the top n scorers for each paper are saved as alternates (aggregate_scores)
                'constraints': {},  # leaving around just in case there is a need for constraints again
                'custom_loads': {}, # leaving this around since there was some talk of not doing edge custom-loads
                'config_invitation': self.conf_ids.CONFIG_ID,
                'paper_invitation': self.conference.get_blind_submission_id(),
                'assignment_invitation': self.get_paper_assignment_id(),
                'match_group': self.conference.get_reviewers_id(),
                'status': 'Initialized'
            }
        })
        self.add_config_custom_loads()
        self.add_config_constraints()
        self.config_note.content[Configuration.SCORES_SPECIFICATION] = self.params.scores_config[Params.SCORES_SPEC]
        self.config_note.content[Configuration.AGGREGATE_SCORE_INVITATION] = self.conf_ids.AGGREGATE_SCORE_ID
        self.config_note.content[Configuration.CONFLICTS_INVITATION_ID] = self.conf_ids.CONFLICTS_INV_ID
        self.config_note.content[Configuration.CUSTOM_LOAD_INVITATION_ID] = self.conf_ids.CUSTOM_LOAD_INV_ID


    def post_config_note (self):
        self.config_note = self.client.post_note(self.config_note)
        self._config_note_id = self.config_note.id


    def add_config_constraints(self):
        if self.params.constraints_vetos != {}:
            self.create_constraint_edges(self.params.constraints_vetos, Configuration.VETO)
        if self.params.constraints_locks != {}:
            self.create_constraint_edges(self.params.constraints_locks, Configuration.LOCK)


    # constraints is a dictionary mapping paper indices to list of reviewer indices.
    # N.B. THe constraint label is the configuration title.  THe weight is '-inf' or '+inf' A NON-NUMBER!!
    def create_constraint_edges (self, constraints, val):
        constraint_edge_inv = self.conf_ids.CONSTRAINTS_INV_ID
        edges = []
        for paper_ix, reviewers_list in constraints.items():
            p = self.paper_notes[paper_ix]
            for reviewer_ix in reviewers_list:
                r = self.reviewers[reviewer_ix]
                e = openreview.Edge(head=p.id, tail=r, label=self.config_title, weight=val, invitation=constraint_edge_inv,
                                    readers=[self.conf_ids.CONF_ID], writers=[self.conf_ids.CONF_ID], signatures=[r])
                edges.append(e)
        openreview.tools.post_bulk_edges(self.client, edges)


    def add_config_custom_loads (self):
        '''
        The supply deduction > 0 indicates that some reviewers cannot do the default minimum number of reviews and
        we want to cycle through the reviewers lowering their loads until the supply deduction is met.
        :return:
        '''
        loads = {reviewer: self.params.reviewer_max_papers for reviewer in self.reviewers}
        if self.params.custom_load_supply_deduction:
            self.reduce_reviewer_loads(loads, self.params.custom_load_supply_deduction)
        elif self.params.custom_load_map != {}:
            self.set_reviewer_loads(loads, self.params.custom_load_map)
        # build custom_load edge for those reviewers that are different from the default max
        edges = []
        for rev, load in loads.items():
            if load != self.params.reviewer_max_papers:
                edge = openreview.Edge(invitation=self.conf_ids.CUSTOM_LOAD_INV_ID, label=self.config_title, head=self.conf_ids.CONF_ID, tail=rev, weight=load, readers=[self.conf_ids.CONF_ID], writers=[self.conf_ids.CONF_ID], signatures=[self.conf_ids.CONF_ID])
                edges.append(edge)
        openreview.tools.post_bulk_edges(self.client, edges)

    # The Params specify custom load settings for reviewers based on index of reviewer.
    def set_reviewer_loads (self, loads, custom_load_map):
        for rev_ix, load in custom_load_map.items():
            reviewer = self.reviewers[rev_ix]
            loads[reviewer] = load

    def reduce_reviewer_loads (self, loads, shortfall):
        count = shortfall
        keys = cycle(self.reviewers)
        for k in keys:
            loads[k] -= 1
            count -= 1
            if count == 0:
                break


    def get_reviewer (self, index):
        return self.reviewers[index]


    ## Below are routines some of which could go into the matching portion of the conference builder

    def get_paper (self, forum_id):
        for p in self.paper_notes:
            if p.id == forum_id:
                return p
        return None


    # returns constraints as dict of {forum-id0: {reviewer-0: '-inf', reviewer=1: '+inf'}, forum_id1 ... }
    def get_constraints (self):
        d = defaultdict(defaultdict)
        for edge in self.get_constraints_edges():
            forum_id = edge.head
            reviewer = edge.tail
            d[forum_id][reviewer] = edge.weight
        return d

    # returns custom-load info as a dict {reviewer-0: load, review-1: load}
    def get_custom_loads (self):
        return {edge.tail: edge.weight for edge in self.get_custom_loads_edges()}

    # return papers and their user conflicts as dictionary of forum_ids mapped to lists of users that conflict with the paper.
    def get_conflicts_from_edges (self):
        d = defaultdict(list)
        edges = openreview.tools.iterget_edges(self.client, invitation=self.conf_ids.CONFLICTS_INV_ID)
        for e in edges:
            forum_id = e.head
            reviewer = e.tail
            conflicts = e.label
            d[forum_id].append(reviewer)
        return d

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

    def get_paper_note_ids (self):
        return [p.id for p in self.get_paper_notes()]

    def get_config_note_status (self):
        config_note = self.get_config_note()
        return config_note.content[Configuration.STATUS]

    def get_assignment_notes (self):
        # return self.conference.get_assignment_notes()   # cannot call this until released
        return self.client.get_notes(invitation=self.get_paper_assignment_id())


    def get_assignment_note_assigned_reviewers (self, assignment_note):
        return assignment_note.content[Assignment.ASSIGNED_GROUPS]

    def get_assignment_edges (self):
        '''
        :return: a list of the conferences assignment edges
        '''
        assignment_inv_id = self.conf_ids.ASSIGNMENT_ID
        edges = openreview.tools.iterget_edges(self.client, invitation=assignment_inv_id)
        return list(edges)

    def get_assignment_edge (self, paper_id, reviewer ):
        assignment_inv_id = self.conf_ids.ASSIGNMENT_ID
        edges = self.client.get_edges(invitation=assignment_inv_id, head=paper_id, tail=reviewer)
        if edges:
            return edges[0]
        else:
            return None



    def get_assignment_edges_by_reviewer (self, reviewer ):
        assignment_inv_id = self.conf_ids.ASSIGNMENT_ID
        edges = self.client.get_edges(invitation=assignment_inv_id, tail=reviewer)
        if edges:
            return edges
        else:
            return []

    def get_aggregate_score_edges (self):
        '''
        :return: a list of the conferences aggregate edges
        '''
        agg_inv_id = self.conf_ids.AGGREGATE_SCORE_ID
        edges = openreview.tools.iterget_edges(self.client, invitation=agg_inv_id, limit=10000)
        return list(edges)

    def get_custom_loads_edges (self):
        return openreview.tools.iterget_edges(self.client, invitation=self.conf_ids.CUSTOM_LOAD_INV_ID, label=self.config_title)

    def get_constraints_edges (self):
        return openreview.tools.iterget_edges(self.client, invitation=self.conf_ids.CONSTRAINTS_INV_ID, label=self.config_title)