from matcher.fields import Assignment, Configuration
from collections import defaultdict

class AssignmentChecker:


    def __init__(self, conf):
        self.conf = conf
        self.constraints =  self.conf.get_constraints()
        self.conflicts = self.conf.get_conflicts()
        self.assignment_notes = self.conf.get_assignment_notes()


    def count_user_reviews(self):
        '''
        :return: a map of reviewers to a count of how many papers they are reviewing.
        '''
        review_counts = defaultdict(int)
        for note in self.assignment_notes:
            assignment = self.conf.get_assignment_note_assigned_reviewers(note)
            for reviewer_info in assignment:
                user = reviewer_info[Assignment.USERID]
                review_counts[user] += 1
        return review_counts


    def is_paper_assigned_to_reviewer(self, forum_id, reviewer):
        note = self.conf.get_assignment_note(forum_id)
        if not note:
            return False
        for user_data in self.conf.get_assignment_note_assigned_reviewers(note):
            if user_data[Assignment.USERID] == reviewer:
                return True
        return False





