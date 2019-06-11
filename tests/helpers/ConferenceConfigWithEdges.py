import time
import json
from collections import defaultdict
from helpers.ConferenceConfig import ConferenceConfig
from matcher.fields import Configuration
import openreview
from openreview import Edge, Invitation
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
from helpers.Params import Params
from itertools import cycle

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
        # super().customize_config_invitation()
        config_inv = self.client.get_invitation(id=self.get_assignment_configuration_id())
        self.update_score_spec()
        self.build_score_invitations()
        if config_inv:
            content = config_inv.reply['content']
            # content[Configuration.SCORES_INVITATIONS] = {'order': 16, 'required': True, 'description': 'Score edge invitations',
            #                                              'values': self.score_invitation_ids}
            content[Configuration.SCORES_SPECIFICATION] = {'order': 16, 'required': True, 'description': 'Score specification JSON',
                                                         'value-dict': {}}
            content[Configuration.AGGREGATE_SCORE_INVITATION] = {'order': 17, 'required': True, 'description': 'Aggregrate Score invitation',
                                                                 'value': self.conf_ids.AGGREGATE_SCORE_ID}
            content[Configuration.CONFLICTS_INVITATION_ID] = {'order': 18, 'required': True, 'description': 'Conflicts invitation',
                                                                 'value': self.conf_ids.CONFLICTS_INV_ID}
            content[Configuration.CONSTRAINTS_INVITATION_ID] = {'order': 19, 'required': True, 'description': 'Constraints invitation',
                                                                 'value': self.conf_ids.CONSTRAINTS_INV_ID}
            content[Configuration.CUSTOM_LOAD_INVITATION_ID] = {'order': 20, 'required': True, 'description': 'Custom-load invitation',
                                                                 'value': self.conf_ids.CUSTOM_LOAD_INV_ID}
            self.client.post_invitation(config_inv)

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
            inv = Invitation(id=inv_id, reply={'content': {'edge': {'head': 'note', 'tail': 'group'}}})
            inv = self.client.post_invitation(inv)
            self._score_invitations.append(inv)

        inv_id = self.conf_ids.AGGREGATE_SCORE_ID
        inv = Invitation(id=inv_id, reply={'content': {'edge': {'head': 'note', 'tail': 'group'}}})
        self.aggregate_score_invitation = self.client.post_invitation(inv)

    # builds the assignment edge invitation.
    def build_assignment_invitations (self):
        self.assignment_inv = Invitation(id=self.conf_ids.ASSIGNMENT_ID, reply={'content': {'edge': {'head': 'note', 'tail': 'group'}}})
        self.assignment_inv = self.client.post_invitation(self.assignment_inv)


    def create_config_note (self):
        super().create_config_note()
        # self.config_note.content[Configuration.SCORES_INVITATIONS] = [inv.id for inv in self.score_invitations]
        self.config_note.content[Configuration.SCORES_SPECIFICATION] = self.params.scores_config[Params.SCORES_SPEC]
        self.config_note.content[Configuration.AGGREGATE_SCORE_INVITATION] = self.aggregate_score_invitation.id
        self.config_note.content[Configuration.CONFLICTS_INVITATION_ID] = self.conf_ids.CONFLICTS_INV_ID
        self.config_note.content[Configuration.CONSTRAINTS_INVITATION_ID] = self.conf_ids.CONSTRAINTS_INV_ID
        self.config_note.content[Configuration.CUSTOM_LOAD_INVITATION_ID] = self.conf_ids.CUSTOM_LOAD_INV_ID



    def add_reviewer_entries_to_metadata (self):
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
                    score_name = PaperReviewerEdgeInvitationIds.translate_score_inv_to_score_name(score_inv.id)
                    score = self.gen_score(score_name, reviewer_ix=reviewer_ix, paper_ix=paper_ix )
                    if (score == 0 or score == '0') and self.params.scores_config.get(Params.OMIT_ZERO_SCORE_EDGES, False):
                        pass
                    elif isinstance(score, str):
                        edge = Edge(head=paper_note.id, tail=reviewer, label=score, weight=0, invitation=score_inv.id, readers=['everyone'], writers=[self.conf_ids.CONF_ID], signatures=[reviewer])
                        edge_type_dict[score_inv.id].append(edge)
                    else:
                        edge = Edge(head=paper_note.id, tail=reviewer, label='xx', weight=float(score), invitation=score_inv.id, readers=['everyone'], writers=[self.conf_ids.CONF_ID], signatures=[reviewer])
                        edge_type_dict[score_inv.id].append(edge)

                reviewer_ix += 1
            paper_ix += 1
        for score_edges in edge_type_dict.values():
            self.client.post_bulk_edges(score_edges) # can only send one edge type in the bulk list

        if not self._silence:
            print("Time to build score edges: ", time.time() - now)
        self.add_conflicts_to_metadata()

    def get_aggregate_edges (self):
        '''
        :return: a list of the conferences aggregate edges
        '''
        agg_inv_id = self.conf_ids.AGGREGATE_SCORE_ID
        edges = openreview.tools.iterget_edges(self.client, invitation=agg_inv_id)
        return list(edges)

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

    def get_aggregate_score_edge (self, paper_id, reviewer):
        agg_inv_id = self.conf_ids.AGGREGATE_SCORE_ID
        edges = self.client.get_edges(invitation=agg_inv_id, head=paper_id, tail=reviewer)
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

    # meta data notes are not part of conferences built with edges so this skips doing anything with them
    # TODO The conference builder should no longer build metadata notes for each paper
    def build_paper_to_metadata_map (self):
        pass


    def add_conflicts_to_metadata(self):
        edges = []
        for paper_index, user_index_list in self.params.conflicts_config.items():
            paper_note = self.paper_notes[paper_index]
            for user_ix in user_index_list:
                reviewer = self.reviewers[user_ix]
                edge = Edge(head=paper_note.id, tail=reviewer, invitation=self.conf_ids.CONFLICTS_INV_ID, weight=1,
                            label='conflict-exists', readers=['everyone'], writers=[self.conf_ids.CONF_ID], signatures=[reviewer])
                edges.append(edge)
        self.client.post_bulk_edges(edges)


    def reduce_reviewer_loads (self, loads, shortfall):
        count = shortfall
        keys = cycle(self.reviewers)
        for k in keys:
            loads[k] -= 1
            count -= 1
            if count == 0:
                break

    # The Params specify custom load settings for reviewers based on index of reviewer.
    def set_reviewer_loads (self, loads, custom_load_map):
        for rev_ix, load in custom_load_map.items():
            reviewer = self.reviewers[rev_ix]
            loads[reviewer] = load

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
                edge = openreview.Edge(invitation=self.conf_ids.CUSTOM_LOAD_INV_ID, label=self.config_title, head=self.conf_ids.CONF_ID, tail=rev, weight=load, readers=['everyone'], writers=[self.conf_ids.CONF_ID], signatures=[rev])
                edges.append(edge)
        self.client.post_bulk_edges(edges)

    def get_custom_loads_edges (self):
        return openreview.tools.iterget_edges(self.client, invitation=self.conf_ids.CUSTOM_LOAD_INV_ID, label=self.config_title)

    def get_constraints_edges (self):
        return openreview.tools.iterget_edges(self.client, invitation=self.conf_ids.CONSTRAINTS_INV_ID, label=self.config_title)

    # returns custom-load info as a dict {reviewer-0: load, review-1: load}
    def get_custom_loads (self):
        return {edge.tail: edge.weight for edge in self.get_custom_loads_edges()}

    # returns constraints as dict of {forum-id0: {reviewer-0: '-inf', reviewer=1: '+inf'}, forum_id1 ... }
    def get_constraints (self):
        d = defaultdict(defaultdict)
        for edge in self.get_constraints_edges():
            forum_id = edge.head
            reviewer = edge.tail
            d[forum_id][reviewer] = edge.weight
        return d

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
                                    readers=['everyone'], writers=[self.conf_ids.CONF_ID], signatures=[r])
                edges.append(e)
        self.client.post_bulk_edges(edges)

    def get_score_edges (self, paper, reviewer):
        edges = []
        for score_inv in self.score_invitations:
            e = self.client.get_edges(invitation=score_inv.id, head=paper.id, tail=reviewer)
            if e:
                e = e[0]
                edges.append(e)
        return edges


