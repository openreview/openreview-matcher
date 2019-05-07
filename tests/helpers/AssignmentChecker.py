from matcher.fields import Assignment, Configuration
from collections import defaultdict
from helpers.ConferenceConfigWithEdges import ConferenceConfigWithEdges

class AssignmentChecker:


    def __init__(self, conf):
        self.conf = conf #type: ConferenceConfigWithEdges


    def count_user_reviews(self):
        '''
        :return: a map of reviewers to a count of how many papers they are reviewing.
        '''
        review_counts = defaultdict(int)
        d = defaultdict(int)
        for e in self.conf.get_assignment_edges():
            d[e.tail] += 1

        return d



    def is_paper_assigned_to_reviewer(self, forum_id, reviewer):
        reviewer_edges = self.conf.get_assignment_edges_by_reviewer(reviewer)
        loc = next((edge for edge in reviewer_edges if edge.head==forum_id), None)
        return loc != None
