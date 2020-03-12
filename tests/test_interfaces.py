import random
from unittest import mock
import pytest
import openreview
from matcher.service.openreview_interface import ConfigNoteInterface, CacheHandler

def mock_client(
            paper_ids,
            reviewer_ids,
            mock_invitations,
            mock_groups,
            mock_notes,
            mock_grouped_edges
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

    client.get_invitation = mock.MagicMock(side_effect=get_invitation)
    client.get_group = mock.MagicMock(side_effect=get_group)
    client.get_note = mock.MagicMock(side_effect=get_note)
    client.get_notes = mock.MagicMock(side_effect=get_notes)
    client.post_note = mock.MagicMock(side_effect=post_note)
    client.get_grouped_edges = mock.MagicMock(side_effect=get_grouped_edges)

    return client

def mock_cache_handler():
    cache_handler = mock.MagicMock(CacheHandler)

    def set_key_prefix(key_prefix):
        return ''

    def get_value(key):
        return False

    def set_value(key, value):
        pass

    cache_handler.set_key_prefix = mock.MagicMock(side_effect=set_key_prefix)
    cache_handler.get_value = mock.MagicMock(side_effect=get_value)
    cache_handler.set_value = mock.MagicMock(side_effect=set_value)

    return cache_handler

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
                    'id': {'head': '<config_note_id>'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 1}
                    ]
                }
            ]
        }
    }

    client = mock_client(**mock_openreview_data)

    cache_handler = mock_cache_handler()
    interface = ConfigNoteInterface(client, '<config_note_id>', cache_handler)

    assert interface.match_group.id
    assert interface.reviewers
    assert interface.config_note
    assert interface.paper_notes
    assert interface.papers
    assert interface.minimums
    assert interface.maximums
    assert interface.demands
    assert list(interface.constraints)
    assert interface.scores_by_type
    assert interface.weight_by_type
    assert interface.assignment_invitation
    assert interface.aggregate_score_invitation
    assert interface.custom_load_edges

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
                    'id': {'head': '<config_note_id>'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': 1}
                    ]
                }
            ]
        }
    }

    client = mock_client(**mock_openreview_data)

    cache_handler = mock_cache_handler()
    interface = ConfigNoteInterface(client, '<config_note_id>', cache_handler)

    assert interface.match_group.id
    assert interface.reviewers
    assert interface.config_note
    assert interface.paper_notes
    assert interface.papers
    assert interface.minimums
    assert interface.maximums
    assert interface.demands
    assert list(interface.constraints)
    assert not interface.scores_by_type
    assert not interface.weight_by_type
    assert interface.assignment_invitation
    assert interface.aggregate_score_invitation
    assert interface.custom_load_edges

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
                    'id': {'head': '<config_note_id>'},
                    'values': [
                        {'tail': 'reviewer0', 'weight': -9.4}
                    ]
                }
            ]
        }
    }

    client = mock_client(**mock_openreview_data)

    cache_handler = mock_cache_handler()
    interface = ConfigNoteInterface(client, '<config_note_id>', cache_handler)

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
                    'id': {'head': '<config_note_id>'},
                    'values': [
                        {
                            'tail': 'reviewer3',
                            'weight': 3
                        }
                    ]
                }
            ]
        }
    }

    client = mock_client(**mock_openreview_data)

    cache_handler = mock_cache_handler()
    interface = ConfigNoteInterface(client, '<config_note_id>', cache_handler)

    for reviewer_index, reviewer in enumerate(interface.reviewers):
        if reviewer == 'reviewer3':
            assert interface.maximums[reviewer_index] == 3
        else:
            assert interface.maximums[reviewer_index] == interface.config_note.content['max_papers']

