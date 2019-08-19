'''
Contains the MatcherClient and MatcherClientMock classes,
as well as helper functions for communicating with the OpenReview instance
and manipulating OpenReview objects.

'''

import re
import logging
from collections import defaultdict

import openreview

class MatcherClient(openreview.Client):
    '''
    A subclass of the openreview.Client object with matching-specific
    attributes and functions.

    Responsible for communicating with the OpenReview server instance.
    '''
    def __init__(self, username='', password='', baseurl='', config_id='', logger=logging.getLogger(__name__)):
        super().__init__(username=username, password=password, baseurl=baseurl)
        self.logger = logger

        self.config_note = self.get_note(config_id)
        self._get_match_data()

    def _get_match_data(self):
        '''Retrieve all the OpenReview objects necessary for the match'''

        self.papers = list(openreview.tools.iterget_notes(
            self, invitation=self.config_note.content['paper_invitation']))

        self.match_group = self.get_group(self.config_note.content['match_group'])
        self.reviewers = self.match_group.members

        self.assignment_invitation = self.get_invitation(
            self.config_note.content['assignment_invitation'])

        # scores_specification is a dict, keyed on score invitation ids.
        self.scores_specification = self.config_note.content['scores_specification']

        self.edges_by_invitation = defaultdict(list)
        for invitation_id in self.scores_specification.keys():
            self.edges_by_invitation[invitation_id] = self.get_all_edges(invitation_id)

        self.conflicts_invitation = self.get_invitation(
            self.config_note.content['conflicts_invitation'])

        self.custom_load_invitation = self.get_invitation(
            self.config_note.content['custom_load_invitation'])

        self.aggregate_score_invitation = self.get_invitation(
            self.config_note.content['aggregate_score_invitation'])

        self.custom_load_edges = self.get_all_edges(self.custom_load_invitation.id)
        self.constraint_edges = self.get_all_edges(self.conflicts_invitation.id)

    def get_all_edges(self, edge_invitation_id):
        '''Helper function for retrieving and parsing all edges in bulk'''
        all_edges = []
        limit = 1000
        offset = 0
        done = False

        edge_invitation = self.get_invitation(edge_invitation_id)

        while not done:
            edges_grouped_by_paper = self.get_grouped_edges(
                edge_invitation_id,
                groupby='head',
                select='tail,label,weight',
                limit=limit,
                offset=offset)

            current_batch = []
            for group in edges_grouped_by_paper:
                forum_id = group['id']['head']
                for group_value in group['values']:
                    current_batch.append(_build_edge(
                        edge_invitation,
                        forum_id,
                        group_value['tail'],
                        group_value.get('weight'),
                        group_value.get('label'),
                        None
                    ))

            all_edges.extend(current_batch)
            offset += limit
            if len(current_batch) < limit:
                done = True

        return all_edges

    def save_suggested_assignments(self, assignments_by_forum):
        '''Helper function for posting assignments returned by the Encoder'''
        label = self.config_note.content['title']
        paper_by_forum = {n.forum: n for n in self.papers}

        self.logger.debug('saving {} edges'.format(self.assignment_invitation.id))

        assignment_edges = []
        score_edges = []

        for forum, assignments in assignments_by_forum.items():
            paper = paper_by_forum[forum]

            for paper_user_entry in assignments:
                score = paper_user_entry.aggregate_score
                user = paper_user_entry.user

                assignment_edges.append(
                    _build_edge(
                        self.assignment_invitation, forum, user, score, label, paper.number)
                )

                score_edges.append(
                    _build_edge(
                        self.aggregate_score_invitation, forum, user, score, label, paper.number)
                )

        openreview.tools.post_bulk_edges(self, assignment_edges)
        openreview.tools.post_bulk_edges(self, score_edges)
        self.logger.debug('posted {} assignment edges'.format(len(assignment_edges)))
        self.logger.debug('posted {} aggregate score edges'.format(len(score_edges)))

    def save_suggested_alternates(self, alternates_by_forum):
        '''Helper function for posting alternates returned by the Encoder'''

        label = self.config_note.content['title']

        paper_by_forum = {n.forum: n for n in self.papers}

        self.logger.debug('Saving aggregate score edges for alternates')

        score_edges = []
        for forum, assignments in alternates_by_forum.items():
            paper = paper_by_forum[forum]

            for paper_user_entry in assignments:
                score = paper_user_entry.aggregate_score
                user = paper_user_entry.user

                score_edges.append(
                    _build_edge(
                        self.aggregate_score_invitation, forum, user, score, label, paper.number)
                )

        openreview.tools.post_bulk_edges(self, score_edges)
        self.logger.debug('posted {} aggregate score edges for alternates'.format(len(score_edges)))

    def set_status(self, status, message=''):
        '''Set the status of the config note'''
        self.config_note.content['status'] = status

        if message:
            self.config_note.content['error_message'] = message

        self.config_note = self.post_note(self.config_note)
        self.logger.debug('status set to:' + self.config_note.content['status'])

def _get_values(invitation, number, property):
    '''Return values compatible with the field `property` in invitation.reply.content'''
    values = []

    property_params = invitation.reply.get(property, {})
    if 'values' in property_params:
        values = property_params.get('values', [])
    elif 'values-regex' in property_params:
        regex_pattern = property_params['values-regex']
        values = []

        for group_id in regex_pattern.split('|'):
            if 'Paper.*' in group_id:
                group_id.replace('Paper.*', 'Paper{}'.format(number))

            if re.match(regex_pattern, group_id):
                values.append(group_id)

    return values

def _build_edge(invitation, forum_id, reviewer, score, label, number):
    '''
    Helper function for constructing an openreview.Edge object.
    Readers, nonreaders, writers, and signatures are automatically filled based on the invitaiton.
    '''
    return openreview.Edge(
        head = forum_id,
        tail = reviewer,
        weight = score,
        label = label,
        invitation = invitation.id,
        readers = _get_values(invitation, number, 'readers'),
        nonreaders = _get_values(invitation, number, 'nonreaders'),
        writers = _get_values(invitation, number, 'writers'),
        signatures = _get_values(invitation, number, 'signatures'))

class MatcherClientMock:
    '''Mock version of the MatcherClient class, used for testing'''
    def __init__(
        self,
        reviewers=[],
        papers=[],
        constraint_edges=[],
        edges_by_invitation=[],
        custom_load_edges=[],
        aggregate_score_invitation=None,
        assignment_invitation=None):

        self.reviewers = reviewers
        self.papers = papers
        self.constraint_edges = constraint_edges
        self.edges_by_invitation = edges_by_invitation
        self.custom_load_edges = custom_load_edges
        self.aggregate_score_invitation = aggregate_score_invitation
        self.assignment_invitation = assignment_invitation

    def set_status(self, status, message=None):
        '''Mock version of the MatcherClient function with the same name.'''
        pass

    def save_suggested_assignments(self, assignments_by_forum):
        '''Mock version of the MatcherClient function with the same name.'''
        pass

    def save_suggested_alternates(self, alternates_by_forum):
        '''Mock version of the MatcherClient function with the same name.'''
        pass

