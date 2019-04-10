import random
import time

from exceptions import NotFoundError
from helpers.ConferenceConfig import ConferenceConfig, ConfIds
from matcher.fields import Configuration
import openreview
from openreview import Edge, Invitation

from params import Params


class ConferenceConfigWithEdges (ConferenceConfig):

    def __init__(self, client, suffix_num, params):
        self._score_invitations = []
        super().__init__(client, suffix_num, params)
        self.build_assignment_invitations()


    @property
    def score_invitations (self):
        return self._score_invitations

    @property
    def score_invitation_ids (self):
        return [inv.id for inv in self.score_invitations]

    def customize_config_invitation (self):
        super().customize_config_invitation()
        config_inv = self.client.get_invitation(id=self.get_assignment_configuration_id())
        # config_inv = self.client.get_invitation(id=self.get_assignment_configuration_id())
        self.build_score_invitations()
        if config_inv:
            content = config_inv.reply['content']
            content[Configuration.SCORES_INVITATIONS] = {'order': 16, 'required': True, 'description': 'Score edge invitations',
                                                         'values': self.score_invitation_ids}
            content[Configuration.AGGREGATE_SCORE_INVITATION] = {'order': 17, 'required': True, 'description': 'Aggregrate Score invitation',
                                                                 'value': self.conf_ids.AGGREGATE_SCORE_ID}
            self.client.post_invitation(config_inv)

    def build_score_invitations (self):
        '''
        build only the invitations for the scores specified in the configuration parameters.  Also builds a score_invitation
        '''
        score_names = self.params.scores_config[Params.SCORE_NAMES_LIST]
        for name in score_names:
            inv_id = self.conf_ids.CONF_ID + '/-/' + name
            inv = Invitation(id=inv_id)
            inv = self.client.post_invitation(inv)
            self._score_invitations.append(inv)

        inv_id = self.conf_ids.AGGREGATE_SCORE_ID
        inv = Invitation(id=inv_id)
        self.aggregate_score_invitation = self.client.post_invitation(inv)

    # builds the assignment edge invitation.
    def build_assignment_invitations (self):
        self.assignment_inv = Invitation(id=self.conf_ids.ASSIGNMENT_ID)
        self.assignment_inv = self.client.post_invitation(self.assignment_inv)


    def create_config_note (self):
        super().create_config_note()
        self.config_note.content[Configuration.SCORES_INVITATIONS] = [inv.id for inv in self.score_invitations]
        self.config_note.content[Configuration.AGGREGATE_SCORE_INVITATION] = self.aggregate_score_invitation.id


    def add_reviewer_entries_to_metadata (self):
        print("Starting to build score edges")
        now = time.time()
        # create the invitations for the score edges now that other parts of the conference have been built
        # self.build_score_invitations()
        paper_notes = self.get_paper_notes()
        reviewers_group = self.client.get_group(self.conference.get_reviewers_id())
        reviewers = reviewers_group.members
        paper_ix = 0
        edges = []
        for paper_note in paper_notes:
            reviewer_ix = 0
            for reviewer in reviewers:
                for score_inv in self.score_invitations:
                    score = self.gen_score(reviewer_ix=reviewer_ix, paper_ix=paper_ix )
                    edge = Edge(head=paper_note.id, tail=reviewer, weight=score, invitation=score_inv.id, readers=['everyone'], writers=[self.conf_ids.CONF_ID], signatures=[reviewer])
                    edges.append(edge)
                reviewer_ix += 1
            paper_ix += 1
        self.client.post_bulk_edges(edges)
        print("Time to build score edges: ", time.time() - now)
        self.add_conflicts_to_metadata()

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
            raise NotFoundError("Edge not found for {} and {}->{}".format(assignment_inv_id, paper_id, reviewer))

    def get_aggregate_score_edges (self):
        '''
        :return: a list of the conferences aggregate edges
        '''
        agg_inv_id = self.conf_ids.AGGREGATE_SCORE_ID
        edges = openreview.tools.iterget_edges(self.client, invitation=agg_inv_id, limit=10000)
        return list(edges)

    # adds in conflicts as edges between papers/reviewers as specified in params.
    # params.conflicts_config is dict that maps paper indices to list of user indices that conflict with the paper
    #
    def add_conflict (self, metadata_note, reviewer):
        super().add_conflict(metadata_note, reviewer) #todo for now
        # for paper_index, user_index_list in self.params.conflicts_config.items():
        #     paper_note = self.paper_notes[paper_index]
        #     for user_ix in user_index_list:
        #         reviewer = self.reviewers[user_ix]
        #         edge = Edge(head=paper_note, tail=reviewer, invitation=self.config_wrapper.get_conflict_edge_invitation())
        #         self.client.post_edge(edge)

    def add_config_custom_loads (self):
        super().add_config_custom_loads() # todo for now
        # if self.params.custom_load_supply_deduction:
        #     reviewers_group = self.client.get_group(self.conference.get_reviewers_id())
        #     config_note = self.get_config_note()
        #     reviewers = reviewers_group.members
        #     default_load = self.params.reviewer_max_papers
        #     deduction = 0
        #     reviewer_ix = 0
        #     # build a map of reviewers to their loads starting with default max and cycling through reducing until
        #     # hit the supply deduction
        #     reviewer_loads = {}
        #     for r in reviewers:
        #         reviewer_loads[r] = default_load
        #     while deduction < self.params.custom_load_supply_deduction:
        #         r = reviewers[reviewer_ix]
        #         reviewer_loads[r] -= 1
        #         reviewer_ix += 1
        #         deduction += 1
        #     # build edges from this map
        #     for reviewer, load in reviewer_loads.items():
        #         edge = Edge(head=config_note, tail=reviewer, weight=load, invitation=self.config_wrapper.get_custom_load_edge_invitation())
        #         self.client.post_edge(edge)

    def add_config_constraints(self):
        super().add_config_constraints() # for now we'll let this go into the config note.
        # if not self.params.constraints_config:
        #     return
        # self.create_constraint_edges(self.params.constraints_vetos, 'veto')
        # self.create_constraint_edges(self.params.constraints_locks, 'lock')


    # constraints is a dictionary mapping paper indices to list of reviewer indices.
    # N.B. we are no longer representing veto/lock with -inf/+inf.   We now create an edge with a label
    def create_constraint_edges (self, constraints, label):
        pass
        # constraint_edge_inv = self.config_wrapper.get_constraint_edge_invitation()
        # paper_notes = self.get_paper_notes()
        # reviewers_group = self.client.get_group(self.conference.get_reviewers_id())
        # reviewers = reviewers_group.members
        # for paper_ix, reviewers_list in constraints.items():
        #     p = paper_notes[paper_ix]
        #     for reviewer_ix in reviewers_list:
        #         r = reviewers[reviewer_ix]
        #         e = Edge(head=p, tail=r, label=label, invitation=constraint_edge_inv)
        #         self.client.post_edge(e)

    def get_score_edges (self, paper, reviewer):
        edges = []
        for score_inv in self.score_invitations:
            e = self.client.get_edges(invitation=score_inv.id, head=paper.id, tail=reviewer)[0]
            edges.append(e)
        return edges
