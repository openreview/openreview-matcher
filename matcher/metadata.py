import abc
import openreview
from collections import defaultdict
import requests
import numpy as np

from . import utils

class OpenReviewFeature(object):
  """
  Defines an abstract base class for OpenReview matching features.

  Classes that extend this object must implement a method called "score" with the following arguments: (signature, forum)

  Example:

  def score(signature, forum):
    ## compute feature score
    return score

  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def score(self, signature, forum):
    """
    @signature - tilde ID of user
    @forum - forum of paper

    """
    return 0.0

class BasicAffinity(OpenReviewFeature):
  """
  This is an OpenReviewFeature that uses the experimental "expertise ranks" endpoint.
  """

  def __init__(self, name, client, groups, papers):
    """
    client - the openreview.Client object used to make the network calls
    groups - an array of openreview.Group objects representing the groups to be matched
    papers - an array of openreview.Note objects representing the papers to be matched
    """

    self.name = name
    self.client = client
    self.groups = groups
    self.papers = papers

    self.scores_by_user_by_forum = {n.forum: defaultdict(lambda:0) for n in papers}

    for g in groups:
      for n in papers:
        response = requests.get(
          self.client.baseurl+'/reviewers/scores?group={0}&forum={1}'.format(g.id, n.forum),
          headers=self.client.headers)
        self.scores_by_user_by_forum[n.forum].update({r['user']: r['score'] for r in response.json()['scores']})

  def score(self, signature, forum):
    return self.scores_by_user_by_forum[forum][signature]


def generate_metadata_notes(client, papers, metadata_invitation, match_group, score_maps={}, constraint_maps={}):
  """
  Generates a list of metadata notes

  Returns:
    a list of openreview.Note objects, each representing a metadata.

  '''
  Score and constraint maps should be two-dimensional dicts,
  where the first index is the forum ID, and the second index is the user ID.
  '''

  """

  # unpack variables
  papers_by_forum = {n.forum: n for n in papers}

  # make network calls
  print("getting metadata...")
  metadata_notes = [n for n in openreview.utils.get_all_notes(client, metadata_invitation.id) if n.forum in papers_by_forum]
  print("done")
  existing_metadata_by_forum = {m.forum: m for m in metadata_notes}

  default_params = {
    'invitation': metadata_invitation.id,
    'readers': metadata_invitation.reply['readers']['values'],
    'writers': metadata_invitation.reply['writers']['values'],
    'signatures': metadata_invitation.reply['signatures']['values'],
    'content': {'groups':{}}
  }

  new_metadata = []

  for p in papers:
    if p.forum not in existing_metadata_by_forum:
      metadata_params = dict(default_params, **{'forum': p.forum})
    else:
      metadata_params = existing_metadata_by_forum[p.forum].to_json()

    metadata_params['content'] = {'groups': {match_group.id: []}}
    new_entries = []

    for user_id in match_group.members:
      metadata_params['content']['groups'][match_group.id].append({
        'userId': user_id,
        'scores': {name: score_map.get(p.forum, {}).get(user_id, 0) for name, score_map in score_maps.items() if score_map.get(p.forum, {}).get(user_id, 0) > 0},
        'constraints': {name: constraint_map.get(p.forum, {}).get(user_id) for name, constraint_map in constraint_maps.items() if constraint_map.get(p.forum, {}).get(user_id)}
      })

    updated_metadata_note = openreview.Note(**metadata_params)
    new_metadata.append(updated_metadata_note)

  return new_metadata

class Encoder(object):
  def __init__(self, metadata=None, config=None, reviewer_ids=None):

    self.metadata = []
    self.config = {}
    self.reviewer_ids = []

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
      self.encode(metadata, config, reviewer_ids)

  def encode(self, metadata, config, reviewer_ids):
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
          self.cost_matrix[coordinates] = cost(entry['scores'], self.weights)

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
        else:
          alternates_by_forum[forum].append(assignment)


    return assignments_by_forum, alternates_by_forum


def cost(scores, weights, precision=0.01):
  weighted_scores = utils.weight_scores(scores, weights)
  score_sum = sum(weighted_scores.values())
  return -1 * int(score_sum / precision)
