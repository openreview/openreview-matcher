from matcher.fields import Assignment
from collections import defaultdict

class MatchResultChecker:

    def build_reviewer_stats (self, assignment_notes):
        self.reviewer_stats = defaultdict(int)
        self.total_score = 0
        for note in assignment_notes:
            assignment = note.content[Assignment.ASSIGNED_GROUPS]
            for reviewer_info in assignment:
                user = reviewer_info[Assignment.USERID]
                user_score = reviewer_info[Assignment.FINAL_SCORE]
                self.total_score += user_score
                self.reviewer_stats[user] += 1



    def check_assignment_custom_loads (self, custom_loads):
        for reviewer, custom_load in custom_loads.items():
            assert self.reviewer_stats[reviewer] <= custom_load, "Reviewer " + reviewer + " custom_load " +custom_load+ " exceeded.  Papers assigned: " + self.reviewer_stats[reviewer]


    def check_results (self, custom_loads, assignment_notes):
        self.build_reviewer_stats(assignment_notes)
        self.check_assignment_custom_loads(custom_loads)
        print("Final Score of match", self.total_score)

