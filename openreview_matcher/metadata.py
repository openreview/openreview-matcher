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
        client  - the openreview.Client object used to make the network calls
        groupId - the ID of the group being matched
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



    def get_scores(self, group, forum):
        return

    def score(self, signature, forum):
        return self.scores_by_user_by_forum[forum][signature]


def generate_metadata_note(groups, features, note_params):
    """
    Generates a metadata note with features defined in the list @features, for each group in
    the list @groups

    Arguments:
        @groups - a list of openreview.Group objects. Metadata notes will have a separate record for each group in the
            list. Features will be computed against every paper in @papers and every member of each group in @groups.
        @features - a list of OpenReviewFeature objects. Each OpenReviewFeature has a method, "score()", which computes
            a value given a user signature and a forum ID.
        @note_params - a dict giving parameters for the Note object (e.g. forum, invitation, readers, writers, signatures).
            Default values are shown in the variable "params"

    Returns:
        an openreview.Note object representing a metadata.

    """

    params = {
        'forum': None,
        'invitation': None,
        'readers': [],
        'writers': [],
        'signatures':[]
    }

    params.update(note_params)

    for f in features:
        assert isinstance(f, OpenReviewFeature), 'all features must be of type features.OpenReviewFeature'

    metadata_content = {'groups': {group.id: {} for group in groups}}
    for group in groups:
        for signature in group.members:
            featurevec = {f.name: f.score(signature, note_params['forum']) for f in features if f.score(signature, note_params['forum']) > 0}
            if featurevec != {}:
                metadata_content['groups'][group.id][signature] = featurevec

    return openreview.Note(content = metadata_content, **note_params)
