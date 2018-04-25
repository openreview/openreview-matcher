#!/usr/bin/python
import time
import numpy as np
import openreview
from collections import defaultdict
from openreview import tools
from solver import Solver

def match(client, config_note, post=True, append=None):
    '''
    Given a configuration note, and a "Solver" class definition,
    returns a list of assignment openreview.Note objects.

    '''

    label = config_note.content['label']
    existing_config_notes = client.get_notes(invitation=config_note.invitation)
    labeled_config_notes = [c for c in existing_config_notes if c.content['label'] == label]

    if labeled_config_notes:
        assert len(labeled_config_notes) == 1, 'More than one configuration exists with this label'
        existing_config_note = labeled_config_notes[0]
        existing_config_note.content['constraints'].update(config_note.content['constraints'])
        existing_config_note.content['configuration'].update(config_note.content['configuration'])
        config_note = existing_config_note

    # unpack variables
    solver_config = config_note.content['configuration']
    weights = dict(solver_config['weights'])

    paper_invitation_id = config_note.content['paper_invitation']
    metadata_invitation_id = config_note.content['metadata_invitation']
    match_group_id = config_note.content['match_group']
    constraints = config_note.content.get('constraints', {})
    assignment_invitation_id = config_note.content['assignment_invitation']

    # make network calls
    papers = tools.get_all_notes(client, paper_invitation_id)
    papers_by_forum = {n.forum: n for n in papers}
    metadata_notes = [n for n in tools.get_all_notes(client, metadata_invitation_id) if n.forum in papers_by_forum]
    match_group = client.get_group(id = match_group_id)
    assignment_invitation = client.get_invitation(assignment_invitation_id)
    existing_assignment_notes = tools.get_all_notes(client, assignment_invitation_id)

    # organize data into indices
    existing_assignments = {n.forum: n.to_json() for n in existing_assignment_notes if n.content['label'] == label}
    entries_by_forum = get_assignment_entries(metadata_notes, weights, constraints, match_group)
    if append:
        append_assignments = {n.forum: n.to_json() for n in existing_assignment_notes if n.content['label'] == append}
    else:
        append_assignments = {}

    # TODO: allow individual constraints
    alphas = [(solver_config['minpapers'], solver_config['maxpapers'])] * len(match_group.members)
    betas = [(solver_config['minusers'], solver_config['maxusers'])] * len(metadata_notes) # why is this the length of the metadata notes?

    score_matrix, hard_constraint_dict, user_by_index, forum_by_index = encode_score_matrix(entries_by_forum)

    solution = Solver(alphas, betas, score_matrix, hard_constraint_dict).solve()

    assigned_userids = decode_score_matrix(solution, user_by_index, forum_by_index)

    new_assignment_notes = build_assignment_notes(
        assigned_userids,
        existing_assignments,
        assignment_invitation,
        config_note,
        entries_by_forum,
        append_assignments=append_assignments
    )

    if post:
        posted_config_note = client.post_note(config_note)

        posted_assignment_notes = []
        for n in new_assignment_notes:
            print("posting assignment for ", n.forum, label)
            posted_assignment_notes.append(client.post_note(n))

        return posted_config_note, posted_assignment_notes
    else:
        return config_note, new_assignment_notes

def get_assignment_entries(metadata_notes, weights, constraints, match_group):
    '''
    Returns a list of dicts that contains info about feature scores per user, per forum.

    e.g. {
        'abcXYZ': [
            {
                'userId': '~Michael_Spector1',
                'scores': {
                    'affinityScore': 0.85
                },
                'constraints': {
                    'brown.edu': '-inf'
                }
                'finalScore': 0.85
            },
            {
                'userId': '~Melisa_Bok1',
                'scores': {
                    'affinityScore': 0.93,
                },
                'constraints': {
                    'umass.edu': '-inf',
                    'cs.umass.edu': '-inf',
                    'iesl.cs.umass.edu': '-inf'
                }
                'finalScore': 0.93
            }
        }
    }

    '''


    def metadata_to_assignment_entry(metadata_entry, forum_constraints):
        '''
        Helper function to convert a metadata entry to an assignment entry.
        '''
        metadata_constraints = metadata_entry.get('constraints', {})
        user_constraints = forum_constraints.get(metadata_entry['userId'])
        if user_constraints:
            metadata_constraints.update({'userConstraint': user_constraints})

        weighted_scores = weight_scores(metadata_entry.get('scores', {}), weights)
        final_score = np.mean([weighted_scores.get(score_type, 0.0) for score_type in weights])

        return {
            'userId': metadata_entry['userId'],
            'scores': weighted_scores,
            'constraints': metadata_constraints,
            'finalScore': final_score
        }


    entries_by_forum = {}
    for m in metadata_notes:
        forum_constraints = constraints.get(m.forum, {})
        assignment_entries = []
        for metadata_entry in m.content['groups'][match_group.id]:
            if metadata_entry['userId'] in match_group.members:
                assignment_entries.append(metadata_to_assignment_entry(metadata_entry, forum_constraints))

        entries_by_forum[m.forum] = assignment_entries

    return entries_by_forum


def weight_scores(scores, weights):
    '''
    multiplies feature values by weights, excepting hard constraints
    '''
    weighted_scores = {}
    for feature in weights:
        if feature in scores:
            weighted_scores[feature] = scores[feature] * weights[feature]

    return weighted_scores

def create_assignment(forum, label, assignment_invitation):
    '''
    Creates the JSON record for an empty assignment Note.

    *important* return type is dict, not openreview.Note
    '''

    return {
        'forum': forum,
        'invitation': assignment_invitation.id,
        'readers': assignment_invitation.reply['readers']['values'],
        'writers': assignment_invitation.reply['writers']['values'],
        'signatures': assignment_invitation.reply['signatures']['values'],
        'content': {
            'label': label
        }
    }

def encode_score_matrix(entries_by_forum):
    '''
    Given a dict of dicts with scores for every user, for every forum,
    encodes the score matrix to be used by the solver.

    Also returns:
    (1) a hard constraint dict (needed by the solver),
    (2) indices needed by the decode_score_matrix() function

    '''

    forums = entries_by_forum.keys()
    num_users = None
    for forum in forums:
        num_users_in_forum = len(entries_by_forum[forum])
        if not num_users:
            num_users = num_users_in_forum
        else:
            assert num_users_in_forum == num_users, "Error: uneven number of user scores by forum"
    if num_users:
        users = [entry['userId'] for entry in entries_by_forum[forums[0]]]

    index_by_user = {user: i for i, user in enumerate(users)}
    index_by_forum = {forum: i for i, forum in enumerate(forums)}

    user_by_index = {i: user for i, user in enumerate(users)}
    forum_by_index = {i: forum for i, forum in enumerate(forums)}

    score_matrix = np.zeros((len(index_by_user), len(index_by_forum)))
    hard_constraint_dict = {}

    for forum, entries in entries_by_forum.iteritems():
        paper_index = index_by_forum[forum]

        #for user, user_scores in weighted_scores_by_user.iteritems():
        for entry in entries:
            user = entry['userId']
            user_scores = entry['scores']
            user_constraints = entry['constraints']
            user_index = index_by_user.get(user, None)

            if user_index:
                coordinates = (user_index, paper_index)
                score_matrix[coordinates] = entry['finalScore']

                if user_constraints:
                    hard_constraint_dict[coordinates] = get_hard_constraint_value(user_constraints.values())

    return score_matrix, hard_constraint_dict, user_by_index, forum_by_index

def decode_score_matrix(solution, user_by_index, forum_by_index):
    '''
    Decodes the 2D score matrix into a returned dict of user IDs keyed by forum ID.

    e.g. {
        'abcXYZ': '~Melisa_Bok1',
        '123-AZ': '~Michael_Spector1'
    }
    '''

    assignments_by_forum = defaultdict(list)
    for var_name in solution:
        var_val = var_name.split('x_')[1].split(',')

        user_index, paper_index = (int(var_val[0]), int(var_val[1]))
        user_id = user_by_index[user_index]
        forum = forum_by_index[paper_index]
        match = solution[var_name]

        if match == 1:
            assignments_by_forum[forum].append(user_id)

    return assignments_by_forum

def build_assignment_notes(assignments, existing_assignments, assignment_invitation, config_note, entries_by_forum, append_assignments={}):
    '''
    Creates or updates (as applicable) the assignment notes with new assignments.

    Returns a list of openreview.Note objects.
    '''

    alternates = config_note.content['configuration']['alternates']
    label = config_note.content['label']
    new_assignment_notes = []
    for forum, userids in assignments.iteritems():
        entries = entries_by_forum[forum]
        assignment = existing_assignments.get(forum, create_assignment(forum, label, assignment_invitation))

        new_content = {
            'assignedGroups': get_assigned_groups(userids, entries),
            'alternateGroups': get_alternate_groups(userids, entries, alternates)
        }

        if append_assignments:
            assignment_to_append = append_assignments.get(forum)
            if assignment_to_append:
                new_content['assignedGroups'] += assignment_to_append['content']['assignedGroups']

        assignment['content'].update(new_content)

        new_assignment_notes.append(openreview.Note(**assignment))

    return new_assignment_notes

def get_assigned_groups(userids, entries):
    '''
    Returns a list of assignment group entries.

    Entries are dicts with the following fields:
        'finalScore'
        'scores'
        'userId'
    '''

    assignment_entries = [e for e in entries if e['userId'] in userids]
    return assignment_entries

def get_alternate_groups(assigned_userids, entries, alternates):
    '''
    Returns a list of alternate group entries.
    The list will have length == @alternates.

    Entries are dicts with the following fields:
        'finalScore'
        'scores'
        'userId'

    '''
    alternate_entries = [e for e in entries if e['userId'] not in assigned_userids]
    valid_alternates = [e for e in alternate_entries if get_hard_constraint_value(e['constraints'].values()) != 0]
    sorted_alternates = sorted(valid_alternates, key=lambda x: x['finalScore'], reverse=True)
    top_n_alternates = sorted_alternates[:alternates]
    return top_n_alternates

def get_hard_constraint_value(score_array):
    """
    A function to check for the presence of Hard Constraints in the score array (+inf or -inf)

    """

    has_neg_constraint = any(['-inf' == c.lower() for c in score_array])
    has_pos_constraint = any(['+inf' == c.lower() for c in score_array])

    if has_neg_constraint:
        return 0
    elif has_pos_constraint:
        return 1
    else:
        return -1

