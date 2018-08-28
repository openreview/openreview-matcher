#!/usr/bin/python
import time
import numpy as np
import openreview
from collections import defaultdict
from openreview import tools
from .solver import Solver

def match(config_note, papers, reviewers, metadata, assignment_invitation):
    '''
    Given a configuration note, and a "Solver" class definition,
    returns a list of assignment openreview.Note objects.

    '''

    label = config_note.content['label']

    # unpack variables
    solver_config = config_note.content['configuration']
    weights = dict(solver_config['weights'])

    paper_invitation_id = config_note.content['paper_invitation']
    metadata_invitation_id = config_note.content['metadata_invitation']
    constraints = config_note.content.get('constraints', {})

    # make network calls
    papers_by_forum = {n.forum: n for n in papers}
    metadata_notes = [n for n in metadata if n.forum in papers_by_forum]

    # organize data into indices
    entries_by_forum = get_assignment_entries(metadata_notes, weights, constraints, reviewers)

    # TODO: allow individual constraints
    alphas = [(solver_config['minpapers'], solver_config['maxpapers'])] * len(reviewers)
    betas = [(solver_config['minusers'], solver_config['maxusers'])] * len(metadata_notes) # why is this the length of the metadata notes?

    score_matrix, hard_constraint_dict, user_by_index, forum_by_index = encode_score_matrix(entries_by_forum)
    print('hard_constraint_dict', hard_constraint_dict)
    solution = Solver(alphas, betas, score_matrix, hard_constraint_dict).solve()

    assigned_userids = decode_score_matrix(solution, user_by_index, forum_by_index)

    new_assignment_notes = build_assignment_notes(
        label, assigned_userids, entries_by_forum, assignment_invitation, num_alternates=5
    )

    return new_assignment_notes

def get_assignment_entries(metadata_notes, weights, constraints, reviewers):
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
        metadata_constraints = {domain: '-inf' for domain in metadata_entry.get('conflicts', [])}

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
        for metadata_entry in m.content['entries']:
            if metadata_entry['userId'] in reviewers:
                assignment_entries.append(metadata_to_assignment_entry(metadata_entry, forum_constraints))

        entries_by_forum[m.forum] = assignment_entries

    return entries_by_forum


def build_assignment_notes(label, assignments, entries_by_forum, assignment_invitation, num_alternates=5):
    '''
    Creates or updates (as applicable) the assignment notes with new assignments.

    Returns a list of openreview.Note objects.
    '''

    new_assignment_notes = []
    for forum, userids in assignments.items():
        entries = entries_by_forum[forum]

        assignment = openreview.Note.from_json({
            'forum': forum,
            'invitation': assignment_invitation.id,
            'readers': assignment_invitation.reply['readers']['values'],
            'writers': assignment_invitation.reply['writers']['values'],
            'signatures': assignment_invitation.reply['signatures']['values'],
            'content': {
                'label': label,
                'assignedGroups': get_assigned_groups(userids, entries),
                'alternateGroups': get_alternate_groups(userids, entries, num_alternates)
            }
        })

        new_assignment_notes.append(assignment)

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

