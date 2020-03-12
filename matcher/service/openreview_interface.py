import re
import openreview
import logging
import redis
import pickle
import time

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

    score = edge.weight

    if translate_map:
        try:
            score = translate_map[edge.label]
        except KeyError:
            raise EncoderError(
                'Cannot translate label {} to score. Valid labels are: {}'.format(
                    edge.label, translate_map.keys()))

    if not isinstance(score, float) and not isinstance(score, int):
        try:
            score = float(score)
        except ValueError:
            raise EncoderError(
                'Edge {} has weight that is neither float nor int: {}, type {}'.format(
                    edge.id, edge.weight, type(edge.weight)))

    return score

def get_all_edges(client, edge_invitation_id, logger=None):
    '''Helper function for retrieving and parsing all edges in bulk'''

    all_edges = []
    logger.debug('GET invitation id={}'.format(edge_invitation_id))
    edge_invitation = client.get_invitation(edge_invitation_id)

    edges_grouped_by_paper = client.get_grouped_edges(
        invitation=edge_invitation_id,
        groupby='head',
        select='tail,label,weight'
    )

    logger.debug('GET grouped edges invitation id={}'.format(edge_invitation_id))
    for group in edges_grouped_by_paper:
        forum_id = group['id']['head']
        for group_value in group['values']:
            all_edges.append(build_edge(
                edge_invitation,
                forum_id,
                group_value['tail'],
                group_value.get('weight'),
                group_value.get('label'),
                None
            ))
    return all_edges

class CacheHandler:
    def __init__(self, host, port, cache_expiration):
        self.redis_client = redis.Redis(host=host, port=port)
        self.cache_expiration = cache_expiration
        self.key_prefix = ''

    def set_key_prefix(self, key_prefix):
        self.key_prefix = key_prefix

    def get_value(self, key):
        serialized_value = self.redis_client.get(self.key_prefix + key)
        if serialized_value:
            return pickle.loads(serialized_value)
        return False

    def set_value(self, key, value):
        serialized_value = pickle.dumps(value)
        self.redis_client.setex(self.key_prefix + key, self.cache_expiration, serialized_value)

class ConfigNoteInterface:
    def __init__(self, client, config_note_id, cache_handler, logger=logging.getLogger(__name__)):
        self.client = client
        self.config_note_id = config_note_id
        self.logger = logger
        self._cache = {}
        # Expire the cache in one day
        if hasattr(client, 'profile'):
            self.profile_id = client.profile.id
        else:
            self.profile_id = 'guest_' + str(time.time())
        self.cache_handler = cache_handler
        self.cache_handler.set_key_prefix(self.profile_id + self.config_note_id)

        for invitation_id in self.config_note.content.get('scores_specification', {}):
            try:
                self.logger.debug('GET invitation id={}'.format(invitation_id))
                self.client.get_invitation(invitation_id)
            except openreview.OpenReviewException as error_handle:
                self.set_status('Error')
                raise error_handle

    @property
    def match_group(self):
        match_group = self.cache_handler.get_value('match_group')
        if not match_group:
            self.logger.debug('GET group id={}'.format(self.config_note.content['match_group']))
            match_group = self.client.get_group(
                self.config_note.content['match_group'])
            self.cache_handler.set_value('match_group', match_group)

        return match_group

    @property
    def reviewers(self):
        return self.match_group.members

    @property
    def config_note(self):
        if not 'config_note' in self._cache:
            self.logger.debug('GET note id={}'.format(self.config_note_id))
            self._cache['config_note'] = self.client.get_note(self.config_note_id)
        return self._cache['config_note']

    @property
    def paper_notes(self):
        paper_notes = self.cache_handler.get_value('paper_notes')
        if not paper_notes:
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
            paper_notes = list(openreview.tools.iterget_notes(
                self.client,
                invitation=paper_invitation,
                content = content_dict))
            self.logger.debug('Count of notes found: {}'.format(len(paper_notes)))
            self.cache_handler.set_value('paper_notes', paper_notes)

        return paper_notes

    @property
    def papers(self):
        return [note.id for note in self.paper_notes]

    @property
    def minimums(self):
        minimums = self.cache_handler.get_value('minimums')
        if not minimums:
            minimums, maximums = self._get_quota_arrays()
            self.cache_handler.set_value('minimums', minimums)
            self.cache_handler.set_value('maximums', maximums)

        return minimums

    @property
    def maximums(self):
        maximums = self.cache_handler.get_value('maximums')
        if not maximums:
            minimums, maximums = self._get_quota_arrays()
            self.cache_handler.set_value('minimums', minimums)
            self.cache_handler.set_value('maximums', maximums)

        return maximums

    @property
    def demands(self):
        demands = self.cache_handler.get_value('demands')
        if not demands:
            demands = [int(self.config_note.content['max_users']) for paper in self.papers]
            self.cache_handler.set_value('demands', demands)

        return demands

    @property
    def num_alternates(self):
        return int(self.config_note.content['alternates'])

    @property
    def constraints(self):
        constraint_edges = self.cache_handler.get_value('constraint_edges')
        if not constraint_edges:
            constraint_edges = get_all_edges(
                self.client, self.config_note.content['conflicts_invitation'], logger=self.logger)
            self.cache_handler.set_value('constraint_edges', constraint_edges)
        for edge in constraint_edges:
            yield edge.head, edge.tail, edge.weight

    @property
    def scores_by_type(self):
        scores_specification = self.config_note.content.get('scores_specification', {})
        edges_by_invitation = self.cache_handler.get_value('edges_by_invitation')
        if not edges_by_invitation:
            edges_by_invitation = {}
            for invitation_id in scores_specification.keys():
                edges_by_invitation[invitation_id] = get_all_edges(
                    self.client, invitation_id, logger=self.logger)

            self.cache_handler.set_value('edges_by_invitation', edges_by_invitation)

        translate_maps = {
            inv_id: score_spec['translate_map'] \
            for inv_id, score_spec in scores_specification.items() \
            if 'translate_map' in score_spec
        }

        return {
            inv_id: [
                (
                    edge.head,
                    edge.tail,
                    _edge_to_score(edge, translate_map=translate_maps.get(inv_id))
                ) for edge in edges] \
            for inv_id, edges in edges_by_invitation.items() \
        }

    @property
    def weight_by_type(self):
        scores_specification = self.config_note.content.get('scores_specification', {})
        return {
            inv_id: entry['weight'] \
            for inv_id, entry in scores_specification.items()
        }

    @property
    def assignment_invitation(self):
        assignment_invitation = self.cache_handler.get_value('assignment_invitation')
        if not assignment_invitation:
            self.logger.debug('GET invitation id={}'.format(self.config_note.content['assignment_invitation']))
            assignment_invitation = self.client.get_invitation(
                self.config_note.content['assignment_invitation'])
            self.cache_handler.set_value('assignment_invitation', assignment_invitation)

        return assignment_invitation

    @property
    def aggregate_score_invitation(self):
        aggregate_score_invitation = self.cache_handler.get_value('aggregate_score_invitation')
        if not aggregate_score_invitation:
            self.logger.debug('GET invitation id={}'.format(self.config_note.content['aggregate_score_invitation']))
            aggregate_score_invitation = self.client.get_invitation(
                self.config_note.content['aggregate_score_invitation'])
            self.cache_handler.set_value('aggregate_score_invitation', aggregate_score_invitation)

        return aggregate_score_invitation

    @property
    def custom_load_edges(self):
        custom_load_edges = self.cache_handler.get_value('custom_load_edges')
        if not custom_load_edges:
            custom_load_edges = get_all_edges(
                self.client, self.config_note.content['custom_load_invitation'], logger=self.logger)
            self.cache_handler.set_value('custom_load_edges', custom_load_edges)

        return custom_load_edges

    def set_status(self, status, message=''):
        '''Set the status of the config note'''
        self.config_note.content['status'] = status

        if message:
            self.config_note.content['error_message'] = message

        self._cache['config_note'] = self.client.post_note(self.config_note)
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
        minimums = [int(self.config_note.content['min_papers']) for r in self.reviewers]
        maximums = [int(self.config_note.content['max_papers']) for r in self.reviewers]

        for edge in self.custom_load_edges:
            try:
                custom_load = int(edge.weight)
            except ValueError:
                raise MatcherError('invalid custom load weight')

            if custom_load < 0:
                custom_load = 0

            index = self.reviewers.index(edge.tail)
            maximums[index] = custom_load

            if custom_load < minimums[index]:
                minimums[index] = custom_load

        return minimums, maximums
