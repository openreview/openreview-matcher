import abc
import openreview

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
        pass



def get_metadata(papers, groups, features):
    """
    Generates
    """

    for f in features:
        assert isinstance(f, OpenReviewFeature), 'all features must be of type features.OpenReviewFeature'

    conf = papers[0].invitation.split('/-/')[0]

    metadata_by_forum = {}

    empty_metadata_params = {
        'invitation': conf + "/-/Paper/Metadata",
        'readers': [conf],
        'writers': [conf],
        'content': {
            'groups': {group.id: {} for group in groups.values()},
        },
        'signatures': [conf]
    }

    for n in papers:
        print "processing metadata: ", n.forum

        if n.forum not in metadata_by_forum:
            metadata_by_forum[n.forum] = openreview.Note(forum = n.forum, **empty_metadata_params)
        else:
            metadata_by_forum[n.forum].content = empty_metadata_params['content'].copy()

        for group in groups.values():
            for signature in group.members:
                feature_vector = {f.name: f.score(signature, n.forum) for f in features}
                metadata_by_forum[n.forum].content['groups'][group.id][signature] = feature_vector

    return metadata_by_forum.values()
