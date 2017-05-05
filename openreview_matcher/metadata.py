import openreview
from features import *

def get_metadata(papers, groups, features):
    """

    """

    for f in features:
        assert isinstance(f, OpenReviewFeature), 'all features must be of type features.OpenReviewFeature'

    CONFERENCE = papers[0].invitation.split('/-/')[0]


    metadata_by_forum = {}

    empty_metadata_params = {
        'invitation': CONFERENCE + "/-/Paper/Metadata",
        'readers': [CONFERENCE],
        'writers': [CONFERENCE],
        'content': {
            'groups': {group.id: {} for group in groups.values()},
        },
        'signatures': [CONFERENCE]
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
