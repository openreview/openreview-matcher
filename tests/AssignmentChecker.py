from matcher.fields import Assignment, Configuration, PaperReviewerScore
from collections import defaultdict
import pprint

class AssignmentChecker:


    def __init__ (self, conf, check_loads, check_constraints, check_conflicts, assignment_notes):
        self.conf = conf
        self.custom_loads = self.conf.get_custom_loads()
        self.constraints =  self.conf.get_constraints()
        self.check_loads = check_loads
        self.check_constraints = check_constraints
        self.check_conflicts = check_conflicts
        self.assignment_notes = assignment_notes

    def check_results(self):
        try:
            self.check_assignment()
            self.count_user_reviews()
            if self.check_loads:
                self.check_custom_loads(self.custom_loads)
            if self.check_constraints:
                self.check_constraint_vetos()
                self.check_constraint_locks()
            if self.check_conflicts:
                self.check_paper_conflicts()
        finally:
            self.show_assignment()

    def count_user_reviews(self):
        self.reviewer_stats = defaultdict(int)
        for note in self.assignment_notes:
            assignment = self.get_assignment_note_assigned_reviewers(note)
            for reviewer_info in assignment:
                user = reviewer_info[Assignment.USERID]
                self.reviewer_stats[user] += 1


    def check_custom_loads (self, custom_loads):
        for reviewer, custom_load in custom_loads.items():
            assert self.reviewer_stats[reviewer] <= custom_load, "Reviewer " + reviewer + \
                    " custom_load " +custom_load+ " exceeded.  Papers assigned: " + self.reviewer_stats[reviewer]

    # assignment must not contain a pairing where a constraint vetos it.
    def check_constraint_vetos(self):
        for note in self.assignment_notes:
            forum_id = note.forum
            reviewer_settings = self.constraints.get(forum_id,{})
            for reviewer, setting in reviewer_settings.items():
                try:
                    if setting == Configuration.VETO:
                        assert not self.has_reviewer(reviewer, self.get_assignment_note_assigned_reviewers(note)), \
                            "Reviewer {} assigned to paper id={}.  But there was a constraint vetoing this".format(reviewer, forum_id)
                except AssertionError as e:
                    print("Assignment note for forum", note.forum, "has content assignedGroups of:")
                    pprint.pprint(self.get_assignment_note_assigned_reviewers(note))
                    raise e

    # all locks in the constraints must result in a corresponding assignment
    def check_constraint_locks(self):
        for forum_id, reviewer_dict in self.constraints.items():
            for reviewer, val in reviewer_dict.items():
                if val == Configuration.LOCK:
                    assert self.is_paper_assigned_to_reviewer(forum_id, reviewer), \
                        "Reviewer {} was locked to paper {} by constraint but not found in assignment".format(reviewer,forum_id)

    def is_paper_assigned_to_reviewer(self, forum_id, reviewer):
        note = self.get_assignment_note(forum_id)
        if not note:
            return False
        for user_data in self.get_assignment_note_assigned_reviewers(note):
            if user_data[Assignment.USERID] == reviewer:
                return True
        return False


    def has_reviewer(self, reviewer, paper_assignment):
        for user_info in paper_assignment:
            if user_info[Assignment.USERID] == reviewer:
                return True
        return False

    def check_paper_conflicts(self):
        for assignment_note in self.assignment_notes:
            forum_id = assignment_note.forum
            for user_info in self.get_assignment_note_assigned_reviewers(assignment_note):
                user = user_info[Assignment.USERID]
                assert not self.conflict_exists(forum_id, user), "Paper {} assigned to {} despite a declared conflict".format(forum_id, user)

    def conflict_exists(self, forum_id, user):
        # get the metadata note for this forum_id and see if the user is in its entries with a conflict
        entries = self.conf.get_metadata_note_entries(forum_id)
        for entry in entries:
            if entry[PaperReviewerScore.USERID] == user and entry.get(PaperReviewerScore.CONFLICTS):
                return True
        return False


    def show_assignment(self):
        print("\nAssignment is:")
        total_score = 0
        for assign_note in self.assignment_notes:
            paper = self.conf.get_paper(assign_note.forum)
            print("Paper", paper.content['title'], assign_note.forum)
            paper_score = 0
            for user_info in self.get_assignment_note_assigned_reviewers(assign_note):
                notation = self.get_notation_for_paper_review(assign_note.forum, user_info[Assignment.USERID])
                print("\t{0:25}: {1:8.2f}  {2:20}".format(user_info[Assignment.USERID], user_info[Assignment.FINAL_SCORE], notation))
                paper_score += user_info[Assignment.FINAL_SCORE]
            print("\t{0:25}: {1:8.2f}".format("",paper_score))
            total_score += paper_score
        print("\t{0:25}: {1:8.2f}".format("Total score",total_score))

    def check_status(self, expected_status):
        config_stat = self.conf.get_config_note_status()
        assert config_stat == expected_status, "Failure: Config status is {} expected {}".format(config_stat, expected_status)

    def check_assignment(self):
        assert len(self.conf.get_assignment_notes()) == len(self.conf.get_paper_notes()), "Number of assignments {} is not same as number of papers {}".\
            format(len(self.conf.get_assignment_notes()), len(self.conf.get_paper_notes()))

    def check_status_complete(self):
        self.check_status(Configuration.STATUS_COMPLETE)

    def get_notation_for_paper_review(self, forum_id, reviewer):
        paper_constraints = self.constraints.get(forum_id)
        if not paper_constraints:
            return ""
        constraint = paper_constraints.get(reviewer)
        if not constraint:
            return ""
        elif constraint == Configuration.LOCK:
            return "by lock constraint"
        elif constraint == Configuration.VETO:
            return "Warning: VETOED BY CONSTRAINT!"

    def get_assignment_note(self, forum_id):
        for note in self.assignment_notes:
            if note.forum == forum_id:
                return note
        return None

    def get_assignment_note_assigned_reviewers (self, assignment_note):
        return assignment_note.content[Assignment.ASSIGNED_GROUPS]



