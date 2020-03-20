import random
from unittest import mock
import pytest
import openreview
from matcher.service.openreview_interface import ConfigNoteInterface

def mock_client(
            paper_ids,
            reviewer_ids,
            mock_invitations,
            mock_groups,
            mock_notes,
            mock_grouped_edges,
            mock_profiles
        ):

    client = mock.MagicMock(openreview.Client)

    def get_invitation(id):
        return mock_invitations[id]

    def get_group(id):
        return mock_groups[id]

    def get_note(id):
        return mock_notes[id]

    def get_notes(invitation, limit=1000, offset=0, **kwargs):
        return mock_notes[invitation][offset:offset+limit]

    def post_note(note):
        mock_notes[note.id] = note
        return mock_notes[note.id]

    def get_grouped_edges(invitation, limit=1000, offset=0, **kwargs):
        return mock_grouped_edges[invitation][offset:offset+limit]

    def search_profiles(ids):
        return mock_profiles

    client.get_invitation = mock.MagicMock(side_effect=get_invitation)
    client.get_group = mock.MagicMock(side_effect=get_group)
    client.get_note = mock.MagicMock(side_effect=get_note)
    client.get_notes = mock.MagicMock(side_effect=get_notes)
    client.post_note = mock.MagicMock(side_effect=post_note)
    client.get_grouped_edges = mock.MagicMock(side_effect=get_grouped_edges)
    client.search_profiles = mock.MagicMock(side_effect=search_profiles)

    return client

def test_confignote_interface():
    '''Test of basic ConfigNoteInterface functionality.'''

    mock_openreview_data = {
        'paper_ids': ['paper0', 'paper1', 'paper2'],
        'reviewer_ids': ['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3'],
        'mock_invitations': {
            '<assignment_invitation_id>': openreview.Invitation(
                    id='<assignment_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<aggregate_score_invitation_id>': openreview.Invitation(
                    id='<aggregate_score_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<custom_load_invitation_id>': openreview.Invitation(
                    id='<custom_load_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<conflicts_invitation_id>': openreview.Invitation(
                    id='<conflicts_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<affinity_score_invitation>': openreview.Invitation(
                    id='<affinity_score_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<bid_invitation>': openreview.Invitation(
                    id='<bid_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
        },
        'mock_groups': {
            '<match_group_id>': openreview.Group(
                    id='<match_group_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    signatories=[],
                    members=['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3']
                )
        },
        'mock_notes': {
            '<config_note_id>': openreview.Note(
                    id='<config_note_id>',
                    readers=[],
                    writers=[],
                    signatures=[],
                    invitation='<config_note_invitation>',
                    content={
                        'match_group': '<match_group_id>',
                        'paper_invitation': '<paper_invitation_id>',
                        'max_users': 1,
                        'min_papers': 1,
                        'max_papers': 1,
                        'alternates': 1,
                        'conflicts_invitation': '<conflicts_invitation_id>',
                        'scores_specification': {
                            '<affinity_score_invitation>': {
                                'weight': 1
                            },
                            '<bid_invitation>': {
                                'weight': 1,
                                'translate_map': {
                                    'High': 1
                                }
                            }
                        },
                        'assignment_invitation': '<assignment_invitation_id>',
                        'aggregate_score_invitation': '<aggregate_score_invitation_id>',
                        'custom_load_invitation': '<custom_load_invitation_id>',
                        'status': None
                    }
                ),
            '<paper_invitation_id>': [
                openreview.Note(
                        id='paper0',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper1',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper2',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    )
                ]
        },
        'mock_grouped_edges': {
            '<affinity_score_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                }
            ],
            '<bid_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                }
            ],
            '<conflicts_invitation_id>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 1},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 1},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 1},
                    ]
                }
            ],
            '<custom_load_invitation_id>': [
                {
                    'id': {'head': '<match_group_id>'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 1}
                    ]
                }
            ]
        },
        'mock_profiles': [
            openreview.Profile(id='reviewer0',
            content={
                'names': [
                    {
                        'username': 'reviewer0'
                    }
                ]
            }),
            openreview.Profile(id='reviewer1',
            content={
                'names': [
                    {
                        'username': 'reviewer1'
                    }
                ]
            }),
            openreview.Profile(id='reviewer2',
            content={
                'names': [
                    {
                        'username': 'reviewer2'
                    }
                ]
            }),
            openreview.Profile(id='reviewer3',
            content={
                'names': [
                    {
                        'username': 'reviewer3'
                    }
                ]
            })
        ]
    }

    client = mock_client(**mock_openreview_data)

    interface = ConfigNoteInterface(client, '<config_note_id>')

    assert interface.reviewers
    assert interface.config_note
    assert interface.papers
    assert interface.minimums
    assert interface.maximums
    assert interface.demands
    assert list(interface.constraints)
    assert interface.scores_by_type
    assert interface.weight_by_type
    assert interface.assignment_invitation
    assert interface.aggregate_score_invitation

    interface.set_status('Running')
    assert interface.config_note.content['status'] == 'Running'

def test_confignote_interface_no_scores_spec():
    '''
    Test of basic ConfigNoteInterface functionality when the scores spec is missing.
    '''

    mock_openreview_data = {
        'paper_ids': ['paper0', 'paper1', 'paper2'],
        'reviewer_ids': ['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3'],
        'mock_invitations': {
            '<assignment_invitation_id>': openreview.Invitation(
                    id='<assignment_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<aggregate_score_invitation_id>': openreview.Invitation(
                    id='<aggregate_score_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<custom_load_invitation_id>': openreview.Invitation(
                    id='<custom_load_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<conflicts_invitation_id>': openreview.Invitation(
                    id='<conflicts_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                )
        },
        'mock_groups': {
            '<match_group_id>': openreview.Group(
                    id='<match_group_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    signatories=[],
                    members=['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3']
                )
        },
        'mock_notes': {
            '<config_note_id>': openreview.Note(
                    id='<config_note_id>',
                    readers=[],
                    writers=[],
                    signatures=[],
                    invitation='<config_note_invitation>',
                    content={
                        'match_group': '<match_group_id>',
                        'paper_invitation': '<paper_invitation_id>',
                        'max_users': 1,
                        'min_papers': 1,
                        'max_papers': 1,
                        'alternates': 1,
                        'conflicts_invitation': '<conflicts_invitation_id>',
                        'assignment_invitation': '<assignment_invitation_id>',
                        'aggregate_score_invitation': '<aggregate_score_invitation_id>',
                        'custom_load_invitation': '<custom_load_invitation_id>',
                        'status': None
                    }
                ),
            '<paper_invitation_id>': [
                openreview.Note(
                        id='paper0',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper1',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper2',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    )
                ]
        },
        'mock_grouped_edges': {
            '<conflicts_invitation_id>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 1},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 1},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 1},
                    ]
                }
            ],
            '<custom_load_invitation_id>': [
                {
                    'id': {'head': '<match_group_id>'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 1}
                    ]
                }
            ]
        },
        'mock_profiles': [
            openreview.Profile(id='reviewer0',
            content={
                'names': [
                    {
                        'username': 'reviewer0'
                    }
                ]
            }),
            openreview.Profile(id='reviewer1',
            content={
                'names': [
                    {
                        'username': 'reviewer1'
                    }
                ]
            }),
            openreview.Profile(id='reviewer2',
            content={
                'names': [
                    {
                        'username': 'reviewer2'
                    }
                ]
            }),
            openreview.Profile(id='reviewer3',
            content={
                'names': [
                    {
                        'username': 'reviewer3'
                    }
                ]
            })
        ]
    }

    client = mock_client(**mock_openreview_data)

    interface = ConfigNoteInterface(client, '<config_note_id>')

    assert interface.reviewers
    assert interface.config_note
    assert interface.papers
    assert interface.minimums
    assert interface.maximums
    assert interface.demands
    assert list(interface.constraints)
    assert not interface.scores_by_type
    assert not interface.weight_by_type
    assert interface.assignment_invitation
    assert interface.aggregate_score_invitation

    interface.set_status('Running')
    assert interface.config_note.content['status'] == 'Running'

def test_confignote_interface_custom_load_negative():
    '''
    Reviewer 0 has a custom load of -9.4, and high scores across the board.

    Custom load should be treated as 0. Reviewer 0 should not be assigned any papers.
    '''

    mock_openreview_data = {
        'paper_ids': ['paper0', 'paper1', 'paper2'],
        'reviewer_ids': ['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3'],
        'mock_invitations': {
            '<assignment_invitation_id>': openreview.Invitation(
                    id='<assignment_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<aggregate_score_invitation_id>': openreview.Invitation(
                    id='<aggregate_score_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<custom_load_invitation_id>': openreview.Invitation(
                    id='<custom_load_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<conflicts_invitation_id>': openreview.Invitation(
                    id='<conflicts_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<affinity_score_invitation>': openreview.Invitation(
                    id='<affinity_score_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<bid_invitation>': openreview.Invitation(
                    id='<bid_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
        },
        'mock_groups': {
            '<match_group_id>': openreview.Group(
                    id='<match_group_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    signatories=[],
                    members=['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3']
                )
        },
        'mock_notes': {
            '<config_note_id>': openreview.Note(
                    id='<config_note_id>',
                    readers=[],
                    writers=[],
                    signatures=[],
                    invitation='<config_note_invitation>',
                    content={
                        'match_group': '<match_group_id>',
                        'paper_invitation': '<paper_invitation_id>',
                        'max_users': 1,
                        'min_papers': 1,
                        'max_papers': 1,
                        'alternates': 1,
                        'conflicts_invitation': '<conflicts_invitation_id>',
                        'scores_specification': {
                            '<affinity_score_invitation>': {
                                'weight': 1
                            },
                            '<bid_invitation>': {
                                'weight': 1,
                                'translate_map': {
                                    'High': 1
                                }
                            }
                        },
                        'assignment_invitation': '<assignment_invitation_id>',
                        'aggregate_score_invitation': '<aggregate_score_invitation_id>',
                        'custom_load_invitation': '<custom_load_invitation_id>',
                        'status': None
                    }
                ),
            '<paper_invitation_id>': [
                openreview.Note(
                        id='paper0',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper1',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper2',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    )
                ]
        },
        'mock_grouped_edges': {
            '<affinity_score_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                }
            ],
            '<bid_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                }
            ],
            '<conflicts_invitation_id>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 1},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 1},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 1},
                    ]
                }
            ],
            '<custom_load_invitation_id>': [
                {
                    'id': {'head': '<match_group_id>'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': -9.4}
                    ]
                }
            ]
        },
        'mock_profiles': [
            openreview.Profile(id='reviewer0',
            content={
                'names': [
                    {
                        'username': 'reviewer0'
                    }
                ]
            }),
            openreview.Profile(id='reviewer1',
            content={
                'names': [
                    {
                        'username': 'reviewer1'
                    }
                ]
            }),
            openreview.Profile(id='reviewer2',
            content={
                'names': [
                    {
                        'username': 'reviewer2'
                    }
                ]
            }),
            openreview.Profile(id='reviewer3',
            content={
                'names': [
                    {
                        'username': 'reviewer3'
                    }
                ]
            })
        ]
    }

    client = mock_client(**mock_openreview_data)

    interface = ConfigNoteInterface(client, '<config_note_id>')

    for reviewer_index, reviewer in enumerate(interface.reviewers):
        if reviewer == 'reviewer0':
            assert interface.maximums[reviewer_index] == 0
        else:
            assert interface.maximums[reviewer_index] == interface.config_note.content['max_papers']


def test_confignote_interface_custom_overload():
    '''
    Default maximum number of assignments per reviewer is 1,
    but reviewer 3 has a custom load of 3.

    '''

    mock_openreview_data = {
        'paper_ids': ['paper0', 'paper1', 'paper2'],
        'reviewer_ids': ['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3'],
        'mock_invitations': {
            '<assignment_invitation_id>': openreview.Invitation(
                    id='<assignment_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<aggregate_score_invitation_id>': openreview.Invitation(
                    id='<aggregate_score_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<custom_load_invitation_id>': openreview.Invitation(
                    id='<custom_load_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<conflicts_invitation_id>': openreview.Invitation(
                    id='<conflicts_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<affinity_score_invitation>': openreview.Invitation(
                    id='<affinity_score_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<bid_invitation>': openreview.Invitation(
                    id='<bid_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
        },
        'mock_groups': {
            '<match_group_id>': openreview.Group(
                    id='<match_group_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    signatories=[],
                    members=['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3']
                )
        },
        'mock_notes': {
            '<config_note_id>': openreview.Note(
                    id='<config_note_id>',
                    readers=[],
                    writers=[],
                    signatures=[],
                    invitation='<config_note_invitation>',
                    content={
                        'match_group': '<match_group_id>',
                        'paper_invitation': '<paper_invitation_id>',
                        'max_users': 1,
                        'min_papers': 1,
                        'max_papers': 1,
                        'alternates': 1,
                        'conflicts_invitation': '<conflicts_invitation_id>',
                        'scores_specification': {
                            '<affinity_score_invitation>': {
                                'weight': 1
                            },
                            '<bid_invitation>': {
                                'weight': 1,
                                'translate_map': {
                                    'High': 1
                                }
                            }
                        },
                        'assignment_invitation': '<assignment_invitation_id>',
                        'aggregate_score_invitation': '<aggregate_score_invitation_id>',
                        'custom_load_invitation': '<custom_load_invitation_id>',
                        'status': None
                    }
                ),
            '<paper_invitation_id>': [
                openreview.Note(
                        id='paper0',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper1',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper2',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    )
                ]
        },
        'mock_grouped_edges': {
            '<affinity_score_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                }
            ],
            '<bid_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                }
            ],
            '<conflicts_invitation_id>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 1},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 1},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 1},
                    ]
                }
            ],
            '<custom_load_invitation_id>': [
                {
                    'id': {'head': '<match_group_id>'},
                    'values': [
                        {
                            'tail': 'reviewer3',
                            'weight': 3
                        }
                    ]
                }
            ]
        },
        'mock_profiles': [
            openreview.Profile(id='reviewer0',
            content={
                'names': [
                    {
                        'username': 'reviewer0'
                    }
                ]
            }),
            openreview.Profile(id='reviewer1',
            content={
                'names': [
                    {
                        'username': 'reviewer1'
                    }
                ]
            }),
            openreview.Profile(id='reviewer2',
            content={
                'names': [
                    {
                        'username': 'reviewer2'
                    }
                ]
            }),
            openreview.Profile(id='reviewer3',
            content={
                'names': [
                    {
                        'username': 'reviewer3'
                    }
                ]
            })
        ]
    }

    client = mock_client(**mock_openreview_data)

    interface = ConfigNoteInterface(client, '<config_note_id>')

    for reviewer_index, reviewer in enumerate(interface.reviewers):
        if reviewer == 'reviewer3':
            assert interface.maximums[reviewer_index] == 3
        else:
            assert interface.maximums[reviewer_index] == interface.config_note.content['max_papers']

def test_confignote_interface_multiple_usernames():
    '''
    Default maximum number of assignments per reviewer is 1,
    but reviewer 3 has a custom load of 3.

    '''

    mock_openreview_data = {
        'paper_ids': ['paper0', 'paper1', 'paper2'],
        'reviewer_ids': ['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3'],
        'mock_invitations': {
            '<assignment_invitation_id>': openreview.Invitation(
                    id='<assignment_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<aggregate_score_invitation_id>': openreview.Invitation(
                    id='<aggregate_score_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<custom_load_invitation_id>': openreview.Invitation(
                    id='<custom_load_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<conflicts_invitation_id>': openreview.Invitation(
                    id='<conflicts_invitation_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<affinity_score_invitation>': openreview.Invitation(
                    id='<affinity_score_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
            '<bid_invitation>': openreview.Invitation(
                    id='<bid_invitation>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    reply={}
                ),
        },
        'mock_groups': {
            '<match_group_id>': openreview.Group(
                    id='<match_group_id>',
                    writers=[],
                    readers=[],
                    signatures=[],
                    signatories=[],
                    members=['reviewer0', 'reviewer1', 'reviewer2', 'reviewer3']
                )
        },
        'mock_notes': {
            '<config_note_id>': openreview.Note(
                    id='<config_note_id>',
                    readers=[],
                    writers=[],
                    signatures=[],
                    invitation='<config_note_invitation>',
                    content={
                        'match_group': '<match_group_id>',
                        'paper_invitation': '<paper_invitation_id>',
                        'max_users': 1,
                        'min_papers': 1,
                        'max_papers': 1,
                        'alternates': 1,
                        'conflicts_invitation': '<conflicts_invitation_id>',
                        'scores_specification': {
                            '<affinity_score_invitation>': {
                                'weight': 1
                            },
                            '<bid_invitation>': {
                                'weight': 1,
                                'translate_map': {
                                    'High': 1
                                }
                            }
                        },
                        'assignment_invitation': '<assignment_invitation_id>',
                        'aggregate_score_invitation': '<aggregate_score_invitation_id>',
                        'custom_load_invitation': '<custom_load_invitation_id>',
                        'status': None
                    }
                ),
            '<paper_invitation_id>': [
                openreview.Note(
                        id='paper0',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper1',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    ),
                openreview.Note(
                        id='paper2',
                        readers=[],
                        writers=[],
                        signatures=[],
                        invitation='<paper_invitation_id>',
                        content={}
                    )
                ]
        },
        'mock_grouped_edges': {
            '<affinity_score_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': random.random()},
                        {'tail': 'reviewer1', 'weight': random.random()},
                        {'tail': 'reviewer2', 'weight': random.random()},
                        {'tail': 'reviewer3', 'weight': random.random()},
                    ]
                }
            ],
            '<bid_invitation>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer21', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer4', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer2', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer21', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer1', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer21', 'weight': None, 'label': 'High'},
                        {'tail': 'reviewer3', 'weight': None, 'label': 'High'},
                    ]
                }
            ],
            '<conflicts_invitation_id>': [
                {
                    'id': {'head': 'paper0'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 1},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper1'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 1},
                        {'tail': 'reviewer3', 'weight': 0},
                    ]
                },
                {
                    'id': {'head': 'paper2'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 0},
                        {'tail': 'reviewer1', 'weight': 0},
                        {'tail': 'reviewer2', 'weight': 0},
                        {'tail': 'reviewer3', 'weight': 1},
                    ]
                }
            ],
            '<custom_load_invitation_id>': [
                {
                    'id': {'head': '<config_note_id>'},
                    'values': [
                        {
                            'tail': 'reviewer3',
                            'weight': 3
                        }
                    ]
                }
            ]
        },
        'mock_profiles': [
            openreview.Profile(id='reviewer0',
            content={
                'names': [
                    {
                        'username': 'reviewer0'
                    }
                ]
            }),
            openreview.Profile(id='reviewer1',
            content={
                'names': [
                    {
                        'username': 'reviewer1'
                    }
                ]
            }),
            openreview.Profile(id='reviewer2',
            content={
                'names': [
                    {
                        'username': 'reviewer2'
                    },
                    {
                        'username': 'reviewer21'
                    }
                ]
            }),
            openreview.Profile(id='reviewer3',
            content={
                'names': [
                    {
                        'username': 'reviewer3'
                    }
                ]
            })
        ]
    }

    client = mock_client(**mock_openreview_data)

    interface = ConfigNoteInterface(client, '<config_note_id>')

    scores_by_type = interface.scores_by_type
    assert scores_by_type
    assert '<bid_invitation>' in scores_by_type
    assert scores_by_type['<bid_invitation>'][0] == ('paper0', 'reviewer0', 1)
    assert scores_by_type['<bid_invitation>'][1] == ('paper0', 'reviewer1', 1)
    assert scores_by_type['<bid_invitation>'][2] == ('paper0', 'reviewer2', 1)
    assert scores_by_type['<bid_invitation>'][3] == ('paper0', 'reviewer3', 1)
    assert scores_by_type['<bid_invitation>'][4] == ('paper1', 'reviewer0', 1)
    assert scores_by_type['<bid_invitation>'][5] == ('paper1', 'reviewer1', 1)
    # Repeated pair of paper-reviewer, we need to decide where the keep only one
    assert scores_by_type['<bid_invitation>'][6] == ('paper1', 'reviewer2', 1)
    assert scores_by_type['<bid_invitation>'][7] == ('paper1', 'reviewer2', 1)
    assert scores_by_type['<bid_invitation>'][8] == ('paper1', 'reviewer3', 1)
    assert scores_by_type['<bid_invitation>'][9] == ('paper2', 'reviewer0', 1)
    assert scores_by_type['<bid_invitation>'][10] == ('paper2', 'reviewer1', 1)
    assert scores_by_type['<bid_invitation>'][11] == ('paper2', 'reviewer2', 1)
    assert scores_by_type['<bid_invitation>'][12] == ('paper2', 'reviewer3', 1)



