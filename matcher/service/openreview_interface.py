import re
import openreview
import logging
from tqdm import tqdm

def build_edge(invitation, forum_id, reviewer, score, label, number):
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
        readers = _get_values(invitation, number, 'readers', forum_id, reviewer),
        nonreaders = _get_values(invitation, number, 'nonreaders'),
        writers = _get_values(invitation, number, 'writers'),
        signatures = _get_values(invitation, number, 'signatures'))

def _get_values(invitation, number, property, head=None, tail=None):
    '''Return values compatible with the field `property` in invitation.reply.content'''
    values = []

    property_params = invitation.reply.get(property, {})
    if 'values' in property_params:
        values = property_params.get('values', [])
    elif 'values-regex' in property_params:
        regex_pattern = property_params['values-regex']
        values = []

        for group_id in regex_pattern.split('|'):
            group_id = group_id.replace('^', '').replace('$', '')
            if 'Paper.*' in group_id:
                group_id = group_id.replace('Paper.*', 'Paper{}'.format(number))
                values.append(group_id)
    elif 'values-copied' in property_params:
        values_copied = property_params['values-copied']

        for value in values_copied:
            if value == '{tail}' :
                values.append(tail)
            elif value == '{head}' :
                values.append(head)
            else:
                values.append(value)

    return values

def _edge_to_score(edge, translate_map=None):
    '''
    Given an openreview.Edge, and a mapping defined by `translate_map`,
    return a numeric score, given an Edge.
    '''

    score = edge['weight']

    if translate_map:
        try:
            score = translate_map[edge['label']]
        except KeyError:
            raise EncoderError(
                'Cannot translate label {} to score. Valid labels are: {}'.format(
                    edge['label'], translate_map.keys()))

    if not isinstance(score, float) and not isinstance(score, int):
        try:
            score = float(score)
        except ValueError:
            raise EncoderError(
                'Edge has weight that is neither float nor int: {}, type {}'.format(
                    edge['weight'], type(edge['weight'])))

    return score

class ConfigNoteInterface:
    def __init__(self, client, config_note_id, logger=logging.getLogger(__name__)):
        self.client = client
        self.logger = logger
        self.logger.debug('GET note id={}'.format(config_note_id))
        self.config_note = self.client.get_note(config_note_id)
        self.logger.debug('GET invitation id={}'.format(self.config_note.content['assignment_invitation']))
        self.assignment_invitation = self.client.get_invitation(self.config_note.content['assignment_invitation'])
        self.logger.debug('GET invitation id={}'.format(self.config_note.content['aggregate_score_invitation']))
        self.aggregate_score_invitation = self.client.get_invitation(self.config_note.content['aggregate_score_invitation'])
        self.num_alternates = int(self.config_note.content['alternates'])


        self._map_reviewers_to_indexes = None
        self._map_papers_to_indexes = None
        self._reviewers = None
        self._papers = None
        self._scores_by_type = None
        self._minimums = None
        self._maximums = None
        self._demands = None
        self._constraints = None

        validate_score_spec()


    def validate_score_spec(self):
        for invitation_id in self.config_note.content.get('scores_specification', {}):
            try:
                self.logger.debug('GET invitation id={}'.format(invitation_id))
                self.client.get_invitation(invitation_id)
            except openreview.OpenReviewException as error_handle:
                self.set_status('Error')
                raise error_handle

    @property
    def reviewers(self):
        if self._reviewers is None:
            self.logger.debug('GET group id={}'.format(self.config_note.content['match_group']))
            match_group = self.client.get_group(self.config_note.content['match_group'])
            self._reviewers = match_group.members
        return self._reviewers

    @property
    def map_reviewers_to_indexes(self):
        if self._map_reviewers_to_indexes is None:
            self._map_reviewers_to_indexes = {r:i for i,r in enumerate(self.reviewers)}
        return self._map_reviewers_to_indexes

    @property
    def papers(self):
        if self._papers is None:
            content_dict = {}
            paper_invitation = self.config_note.content['paper_invitation']
            self.logger.debug('Getting notes for invitation: {}'.format(paper_invitation))
            if '&' in paper_invitation:
                elements = paper_invitation.split('&')
                paper_invitation = elements[0]
                for element in elements[1:]:
                    if element:
                        if element.startswith('content.') and '=' in element:
                            key, value = element.split('.')[1].split('=')
                            content_dict[key] = value
                        else:
                            self.logger.debug('Invalid filter provided in invitation: {}. Supported filter format "content.field_x=value1".'.format(element))
            self._papers = [note.id for note in list(openreview.tools.iterget_notes(
                self.client,
                invitation=paper_invitation,
                content=content_dict))]
            self.logger.debug('Count of notes found: {}'.format(len(self._papers)))

        return self._papers

    @property
    def map_papers_to_indexes(self):
        if self._map_papers_to_indexes is None:
            self._map_papers_to_indexes = {p:i for i,p in enumerate(self.papers)}
        return self._map_papers_to_indexes

    @property
    def minimums(self):
        if self._minimums is None:
            self._get_quota_arrays()

        return self._minimums

    @property
    def maximums(self):
        if self._maximums is None:
            self._get_quota_arrays()

        return self._maximums

    @property
    def demands(self):
        if self._demands is None:
            self._demands = [int(self.config_note.content['max_users']) for paper in self.papers]

        return self._demands

    @property
    def constraints(self):
        if self._constraints is None:
            self._constraints = [(edge['head'], edge['tail'], edge['weight']) for edge in self._get_all_edges(
                self.client,
                self.config_note.content['conflicts_invitation'])]
        return self._constraints

    @property
    def scores_by_type(self):
        scores_specification = self.config_note.content.get('scores_specification', {})

        if self._scores_by_type is None:
            edges_by_invitation = {}
            for invitation_id in scores_specification.keys():
                edges_by_invitation[invitation_id] = self._get_all_edges(
                    self.client,
                    invitation_id)


            translate_maps = {
                inv_id: score_spec['translate_map'] \
                for inv_id, score_spec in scores_specification.items() \
                if 'translate_map' in score_spec
            }

            self._scores_by_type = {
                inv_id: [
                    (
                        edge['head'],
                        edge['tail'],
                        _edge_to_score(edge, translate_map=translate_maps.get(inv_id))
                    ) for edge in edges] \
                for inv_id, edges in self._edges_by_invitation.items() \
            }
        return self._scores_by_type

    @property
    def weight_by_type(self):
        scores_specification = self.config_note.content.get('scores_specification', {})
        return {
            inv_id: entry['weight'] \
            for inv_id, entry in scores_specification.items()
        }

    def set_status(self, status, message=''):
        '''Set the status of the config note'''
        self.config_note.content['status'] = status

        if message:
            self.config_note.content['error_message'] = message

        self._config_note = self.client.post_note(self.config_note)
        self.logger.debug('status set to: {}'.format(self.config_note.content['status']))

    def set_assignments(self, assignments_by_forum):
        '''Helper function for posting assignments returned by the Encoder'''
        label = self.config_note.content['title']
        paper_by_forum = {n.forum: n for n in self.paper_notes}

        self.logger.debug('saving {} edges'.format(self.assignment_invitation.id))

        assignment_edges = []
        score_edges = []

        for forum, assignments in assignments_by_forum.items():
            paper = paper_by_forum[forum]
            for paper_user_entry in assignments:
                score = paper_user_entry['aggregate_score']
                user = paper_user_entry['user']

                assignment_edges.append(
                    build_edge(
                        self.assignment_invitation,
                        forum,
                        user,
                        score,
                        label,
                        paper.number
                    )
                )

                score_edges.append(
                    build_edge(
                        self.aggregate_score_invitation,
                        forum,
                        user,
                        score,
                        label,
                        paper.number
                    )
                )

        openreview.tools.post_bulk_edges(self.client, assignment_edges)
        openreview.tools.post_bulk_edges(self.client, score_edges)
        self.logger.debug('posted {} assignment edges'.format(len(assignment_edges)))
        self.logger.debug('posted {} aggregate score edges'.format(len(score_edges)))

    def set_alternates(self, alternates_by_forum):
        '''Helper function for posting alternates returned by the Encoder'''

        label = self.config_note.content['title']

        paper_by_forum = {n.forum: n for n in self.paper_notes}

        score_edges = []
        for forum, assignments in alternates_by_forum.items():
            paper = paper_by_forum[forum]

            for paper_user_entry in assignments:
                score = paper_user_entry['aggregate_score']
                user = paper_user_entry['user']

                score_edges.append(
                    build_edge(
                        self.aggregate_score_invitation,
                        forum,
                        user,
                        score,
                        label,
                        paper.number
                    )
                )

        openreview.tools.post_bulk_edges(self.client, score_edges)
        self.logger.debug('posted {} aggregate score edges for alternates'.format(len(score_edges)))

    def _get_quota_arrays(self):
        '''get `minimum` and `maximum` reviewer load arrays, accounting for custom loads'''
        self._minimums = [int(self.config_note.content['min_papers']) for r in self.reviewers]
        self._maximums = [int(self.config_note.content['max_papers']) for r in self.reviewers]

        all_reviewers = self.map_reviewers_to_indexes
        edges = []
        edges = self.client.get_grouped_edges(
                invitation = self.config_note.content['custom_load_invitation'],
                head = self.config_note.content['match_group'],
                select='tail,label,weight')
        if edges:
            custom_load_edges = edges[0]['values']

        for edge in self.custom_load_edges:
            if edge['tail'] in all_reviewers:
                try:
                    custom_load = int(edge['weight'])
                except ValueError:
                    raise MatcherError('invalid custom load weight')

                if custom_load < 0:
                    custom_load = 0

                index = self.reviewers.index(edge['tail'])
                self._maximums[index] = custom_load

                if custom_load < minimums[index]:
                    self._minimums[index] = custom_load
            else:
                print('Reviewer {} not found in pool'.format(edge['tail']))

        return minimums, maximums

    def _get_all_edges(self, client, edge_invitation_id):
        '''Helper function for retrieving and parsing all edges in bulk'''

        all_edges = []
        all_papers = self.map_papers_to_indexes
        all_reviewers = self.map_reviewers_to_indexes
        self.logger.debug('GET invitation id={}'.format(edge_invitation_id))

        edges_grouped_by_paper = client.get_grouped_edges(
            invitation=edge_invitation_id,
            groupby='head',
            select='tail,label,weight'
        )

        self.logger.debug('GET grouped edges invitation id={}'.format(edge_invitation_id))
        filtered_edges_groups = list(filter(lambda edge_group: edge_group['id']['head'] in all_papers, edges_grouped_by_paper))

        for group in filtered_edges_groups:
            forum_id = group['id']['head']
            filtered_edges = list(filter(lambda group_value: group_value['tail'] in all_reviewers, group['values']))
            for edge in filtered_edges:
                all_edges.append({
                    'invitation': edge_invitation_id,
                    'head': forum_id,
                    'tail': edge['tail'],
                    'weight': edge.get('weight'),
                    'label': edge.get('label')
                })
        return all_edges
