import abc
import openreview
from collections import defaultdict
import requests
import numpy as np

from . import utils

class Encoder(object):
  def __init__(self, metadata=None, config=None, reviewer_ids=None, cost_func=utils.cost):

    self.metadata = []
    self.config = {}
    self.reviewer_ids = []
    self.cost = cost_func

    self.cost_matrix = np.zeros((0,0))
    self.constraint_matrix = np.zeros((0,0))
    self.entries_by_forum = {}
    self.index_by_forum = {}
    self.index_by_reviewer = {}
    self.forum_by_index = {}
    self.reviewer_by_index = {}

    self.weights = config['weights']
    self.constraints = config['constraints']

    if metadata and config and reviewer_ids:
      self.encode(metadata, config, reviewer_ids, cost_func)

  def encode(self, metadata, config, reviewer_ids, cost_func):
    '''
    Encodes the cost and constraint matrices to be used by the solver.

    metadata    = a list of metadata Notes
    weights     = a dict of weights keyed on score type
      e.g. { 'tpms': 0.5, 'bid': 1.0, 'ac_rec': 2.0 }
    reviewers   = a list of reviewer IDs (to lookup in metadata entries)

    '''
    self.metadata = metadata
    self.config = config
    self.reviewer_ids = reviewer_ids
    self.cost_func = cost_func

    self.cost_matrix = np.zeros((len(self.reviewer_ids), len(self.metadata)))
    self.constraint_matrix = np.zeros(np.shape(self.cost_matrix))

    self.entries_by_forum = { m.forum: { entry['userId']: entry
        for entry in m.content['entries'] }
      for m in self.metadata }

    self.index_by_forum = { m.forum: index
      for index, m in enumerate(self.metadata) }

    self.index_by_reviewer = { r: index
      for index, r in enumerate(self.reviewer_ids) }

    self.forum_by_index = { index: forum
      for forum, index in self.index_by_forum.items() }

    self.reviewer_by_index = { index: id
      for id, index in self.index_by_reviewer.items() }

    self.weights = config['weights']
    self.constraints = config['constraints']

    for forum, entry_by_id in self.entries_by_forum.items():
      paper_index = self.index_by_forum[forum]

      for id, reviewer_index in self.index_by_reviewer.items():
        # first check the metadata entry for scores and conflicts
        coordinates = reviewer_index, paper_index
        entry = entry_by_id.get(id)
        if entry:
          self.cost_matrix[coordinates] = self.cost_func(entry['scores'], self.weights)

          if entry.get('conflicts'):
            self.constraint_matrix[coordinates] = -1
          else:
            self.constraint_matrix[coordinates] = 0

        # overwrite constraints with user-added constraints found in config
        user_constraint = self.constraints.get(forum, {}).get(id)
        if user_constraint:
          if '-inf' in user_constraint:
            self.constraint_matrix[coordinates] = -1
          if '+inf' in user_constraint:
            self.constraint_matrix[coordinates] = 1

  def decode(self, solution):
    '''
    Decodes a solution into assignments
    '''
    flow_matrix = solution[:, :len(self.metadata)]
    overflow = solution[:, len(self.metadata)]

    assignments_by_forum = defaultdict(list)
    alternates_by_forum = defaultdict(list)
    for reviewer_index, reviewer_flows in enumerate(flow_matrix):
      user_id = self.reviewer_by_index[reviewer_index]
      reviewer_overflow = overflow[reviewer_index]

      for paper_index, flow in enumerate(reviewer_flows):
        forum = self.forum_by_index[paper_index]

        assignment = {
          'userId': user_id,
          'scores': None,
          'constraints': None,
          'finalScore': None,
          'availableReviews': reviewer_overflow
        }
        entry = self.entries_by_forum[forum].get(user_id)

        if entry:
          assignment['scores'] = utils.weight_scores(entry.get('scores'), self.weights)
          assignment['constraints'] = entry.get('constraints')
          assignment['finalScore'] = sum(utils.weight_scores(entry.get('scores'), self.weights).values())

        if flow:
          assignments_by_forum[forum].append(assignment)
        elif assignment['availableReviews'] > 0 and assignment['finalScore'] and not assignment['constraints']:
          alternates_by_forum[forum].append(assignment)


    for forum, alternates in alternates_by_forum.items():
      alternates_by_forum[forum] = sorted(alternates, key=lambda a: a['finalScore'], reverse=True)[0:10]

    return dict(assignments_by_forum), dict(alternates_by_forum)




