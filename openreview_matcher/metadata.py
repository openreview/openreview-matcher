import abc
import openreview
from collections import defaultdict
import requests

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
    print "getting metadata...",
    metadata_notes = [n for n in openreview.tools.get_all_notes(client, metadata_invitation.id) if n.forum in papers_by_forum]
    print "done"
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
        try:
            new_entries = metadata_params['content']['groups'][match_group.id] = []
        except KeyError as e:
            print metadata_params
            raise e
        for user_id in match_group.members:
            new_entries.append({
                'userId': user_id,
                'scores': {name: score_map.get(p.forum, {}).get(user_id, 0) for name, score_map in score_maps.iteritems() if score_map.get(p.forum, {}).get(user_id, 0) > 0},
                'constraints': {name: constraint_map.get(p.forum, {}).get(user_id) for name, constraint_map in constraint_maps.iteritems() if constraint_map.get(p.forum, {}).get(user_id)}
            })

        new_metadata.append(openreview.Note(**metadata_params))

    return new_metadata

