#!/usr/bin/python
import time
import numpy as np
import openreview
from collections import defaultdict
from openreview import tools

def match(client, configuration_note, Solver):
    '''
    Given a configuration note, and a "Solver" class definition,
    returns a list of assignment openreview.Note objects.

    '''

    # unpack variables
    label = configuration_note.content['label']
    solver_config = configuration_note.content['configuration']
    weights = dict(solver_config['weights'], **{'userConstraint': 1})

    paper_invitation_id = configuration_note.content['paper_invitation']
    metadata_invitation_id = configuration_note.content['metadata_invitation']
    match_group_id = configuration_note.content['match_group']
    constraints = configuration_note.content['constraints']
    assignment_invitation_id = configuration_note.content['assignment_invitation']

    # make network calls
    papers = tools.get_all_notes(client, paper_invitation_id)
    papers_by_forum = {n.forum: n for n in papers}
    metadata_notes = [n for n in tools.get_all_notes(client, metadata_invitation_id) if n.forum in papers_by_forum]
    match_group = client.get_group(id = match_group_id)
    assignment_invitation = client.get_invitation(assignment_invitation_id)
    existing_assignment_notes = tools.get_all_notes(client, assignment_invitation_id)

    # organize data into indices
    existing_assignments = {n.forum: n.to_json() for n in existing_assignment_notes if n.content['label'] == label}
    entries_by_forum = get_weighted_scores(metadata_notes, weights, constraints, match_group)

    # TODO: allow individual constraints
    alphas = [(solver_config['minpapers'], solver_config['maxpapers'])] * len(match_group.members)
    betas = [(solver_config['minusers'], solver_config['maxusers'])] * len(metadata_notes) # why is this the length of the metadata notes?

    score_matrix, hard_constraint_dict, user_by_index, forum_by_index = encode_score_matrix(entries_by_forum)

    solution = Solver(alphas, betas, score_matrix, hard_constraint_dict).solve()

    assigned_userids = decode_score_matrix(solution, user_by_index, forum_by_index)

    new_assignment_notes = save_assignments(
        assigned_userids,
        existing_assignments,
        assignment_invitation,
        configuration_note,
        entries_by_forum
    )

    return new_assignment_notes

def get_weighted_scores(metadata_notes, weights, constraints, match_group):
    '''
    Returns a list of dicts that contains info about feature scores per user, per forum.

    e.g. {
        'abcXYZ': [
            {
                'userId': '~Michael_Spector1',
                'scores': {
                    'affinityScore': 0.85
                },
                'finalScore': 0.85
            },
            {
                'userId': '~Melisa_Bok1',
                'scores': {
                    'affinityScore': 0.93,
                },
                'finalScore': 0.93
            }
        }
    }

    '''

    entries_by_forum = {}
    for m in metadata_notes:
        user_entries = [e for e in m.content['groups'][match_group.id] if e['userId'] in match_group.members]
        forum_constraints = constraints.get(m.forum, {})
        for entry in user_entries:
            # apply user-defined constraints
            user_constraint = forum_constraints.get(entry['userId'])
            if user_constraint:
                entry['scores'].update({'userConstraint': user_constraint})

            entry['scores'] = weight_scores(entry.get('scores', {}), weights)
            numeric_scores = [score for score in entry['scores'].values() if score != '+inf' and score != '-inf']
            entry['finalScore'] = np.mean(numeric_scores)

        entries_by_forum[m.forum] = user_entries

    return entries_by_forum

def weight_scores(scores, weights):
    '''
    multiplies feature values by weights, excepting hard constraints
    '''
    weighted_scores = {}
    for feature in weights:
        if feature in scores:
            weighted_scores[feature] = scores[feature]

            if scores[feature] != '-inf' and scores[feature] != '+inf':
                weighted_scores[feature] *= weights[feature]

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
            user_index = index_by_user.get(user, None)
            hard_constraint_value = get_hard_constraint_value(user_scores.values())

            if user_index:
                coordinates = (user_index, paper_index)
                if hard_constraint_value == -1:
                    score_matrix[coordinates] = entry['finalScore']
                else:
                    hard_constraint_dict[coordinates] = hard_constraint_value

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

def save_assignments(assignments, existing_assignments, assignment_invitation, configuration_note, entries_by_forum):
    '''
    Creates or updates (as applicable) the assignment notes with new assignments.

    Returns a list of openreview.Note objects.
    '''

    alternates = configuration_note.content['configuration']['alternates']
    label = configuration_note.content['label']
    new_assignment_notes = []
    for forum, userids in assignments.iteritems():
        entries = entries_by_forum[forum]
        assignment = existing_assignments.get(forum, create_assignment(forum, label, assignment_invitation))

        new_content = {
            'assignedGroups': get_assigned_groups(userids, entries),
            'alternateGroups': get_alternate_groups(userids, entries, alternates)
        }

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
    valid_alternates = [e for e in entries if get_hard_constraint_value(e['scores'].values()) != 0]
    sorted_alternates = sorted(valid_alternates, key=lambda x: x['finalScore'], reverse=True)
    top_n_alternates = sorted_alternates[:alternates]
    return top_n_alternates

def get_hard_constraint_value(score_array):
    """
    A function to check for the presence of Hard Constraints in the score array (+Inf or -Inf) ,
    :param score_array:
    :return:
    """
    for element in score_array:
        if str(element).strip().lower() == '+inf':
            return 1
        if str(element).strip().lower() == '-inf':
            return 0
    return -1
