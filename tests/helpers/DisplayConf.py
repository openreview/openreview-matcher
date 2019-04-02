import pprint
from matcher.fields import Assignment, Configuration

class DisplayConf:

    def __init__ (self, conference):
        self.conf = conference

    def show_custom_loads (self):
        print("Custom_loads in config {} are:".format(self.conf.config_note_id))
        pprint.pprint(self.conf.get_custom_loads())

    def show_constraints (self):
        print("Constraints in config {} are:".format(self.conf.config_note_id))
        for forum_id, reviewers in self.conf.get_constraints().items():
            paper_note = self.conf.get_paper(forum_id)
            print(paper_note.content['title'], ' (',forum_id,'): ', end='')
            pprint.pprint(reviewers)

    def show_conflicts (self):
        print("Conflicts in metadata objects are:")
        for forum_id, reviewers in self.conf.get_conflicts().items():
            paper_note = self.conf.get_paper(forum_id)
            print(paper_note.content['title'], ' (',forum_id,'): ', end='')
            pprint.pprint(reviewers)
        pass

    def display_input_structures (self):
        self.show_custom_loads()
        self.show_constraints()
        self.show_conflicts()


    def show_assignment(self):
        '''
        Show the papers and the reviewers assigned along with indication of violations of constraints or conflicts
        :return:
        '''
        assignment_notes = self.conf.get_assignment_notes()
        print("\nAssignment with violations is:")
        total_score = 0
        for assign_note in assignment_notes:
            paper = self.conf.get_paper(assign_note.forum)
            print("AssignmentNote", assign_note.id, "for ", paper.content['title'], '(', assign_note.forum,')')
            paper_score = 0
            for user_info in self.conf.get_assignment_note_assigned_reviewers(assign_note):
                notation = self.get_notation_for_paper_review(assign_note.forum, user_info[Assignment.USERID])
                print("\t{0:25}: {1:8.2f}  {2:20}".format(user_info[Assignment.USERID], user_info[Assignment.FINAL_SCORE], notation))
                paper_score += user_info[Assignment.FINAL_SCORE]
            print("\t{0:25}: {1:8.2f}".format("",paper_score))
            total_score += paper_score
        print("\t{0:25}: {1:8.2f}".format("Total score",total_score))


    def get_notation_for_paper_review(self, forum_id, reviewer):
        paper_constraints = self.conf.get_constraints().get(forum_id)
        paper_conflicts = self.conf.get_conflicts()
        notation = ""
        if reviewer in paper_conflicts[forum_id]:
            notation += "ERROR!: A conflict was declared in metadata!"
        if not paper_constraints:
            return notation
        constraint = paper_constraints.get(reviewer)
        if not constraint:
            return notation
        elif constraint == Configuration.LOCK:
            notation += " Assigned by lock constraint"
        elif constraint == Configuration.VETO:
            notation +=  "ERROR!: VETOED BY CONSTRAINT!"
        return notation