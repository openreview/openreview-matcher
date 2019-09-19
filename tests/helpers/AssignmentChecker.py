from collections import defaultdict
from helpers.ConferenceConfig import ConferenceConfig

class AssignmentChecker:


    def __init__(self, conf):
        self.conf = conf #type: ConferenceConfig


    def count_user_reviews(self):
        '''
        :return: a map of reviewers to a count of how many papers they are reviewing.
        '''
        d = defaultdict(int)
        for e in self.conf.get_assignment_edges():
            d[e.tail] += 1

        return d

    def count_reviewers_assigned_to_paper(self, forum_id, reviewer_ids):
        edges = self.conf.get_assignment_edges()
        return len(list(filter(lambda e: e.head==forum_id and e.tail in reviewer_ids, edges)))

    def is_paper_assigned_to_reviewer(self, forum_id, reviewer):
        reviewer_edges = self.conf.get_assignment_edges_by_reviewer(reviewer)
        loc = next((edge for edge in reviewer_edges if edge.head==forum_id), None)
        return loc != None

