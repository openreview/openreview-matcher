import openreview
import threading
from matcher.solver import Solver
from matcher.encoder import Encoder
from matcher.fields import Configuration
from matcher.fields import PaperReviewerScore
from matcher.fields import Assignment
import logging
import time

class Match:

    def __init__ (self, client, config_note, logger=logging.getLogger(__name__)):
        self.client = client
        self.config_note = config_note
        self.config = self.config_note.content
        self.logger = logger
        self.set_status(Configuration.STATUS_INITIALIZED)

    def set_status (self, status, message=None):
        self.config_note.content[Configuration.STATUS] = status
        if message:
            self.config_note.content[Configuration.ERROR_MESSAGE] = message
        self.client.post_note(self.config_note)
        return self.config_note

    def run (self):
        thread = threading.Thread(target=self.match_task)
        thread.start()

    # A task that runs as a separate thread with errors logged to the app.
    def match_task (self):
        try:
            self.logger.debug("Starting task to assign reviewers for configId: " + self.config_note.id)
            self.config_note = self.compute_match()
        except Exception as e:
            self.logger.error("Failed to complete matching for configId: " + self.config_note.id)
            self.logger.error('Internal error:', exc_info=True)
        finally:
            self.logger.debug("Finished task for configId: " + self.config_note.id)
            return self.config_note


    # A function that can be called from a script to compute a match.
    # Given a config_note and an openreview.client object, this will compute a match of
    # reviewers to papers and post it to the db.  It will return the config note with a status field
    # set to 'complete' if it succeeds.  Otherwise a failure message will be placed in the status field.
    # Pass in a logger if you want logging;  otherwise a default logger will be used.
    def compute_match(self):
        try:
            self.set_status(Configuration.STATUS_RUNNING)
            # TODO I want to stop using the term metadata which means changing the name of this field in the config note
            # and its invitation.
            metadata = list(openreview.tools.iterget_notes(self.client, invitation=self.config['metadata_invitation']))
            self._add_title(metadata)
            reviewer_group = self.client.get_group(self.config['match_group'])
            assignment_inv = self.client.get_invitation(self.config['assignment_invitation'])
            reviewer_ids = reviewer_group.members
            if type(self.config[Configuration.MAX_USERS]) == str:
                demands = [int(self.config[Configuration.MAX_USERS])] * len(metadata)
            else: demands = [self.config[Configuration.MAX_USERS]] * len(metadata)
            if type(self.config[Configuration.MIN_PAPERS]) == str:
                minimums = [int(self.config[Configuration.MIN_PAPERS])] * len(reviewer_ids)
            else: minimums = [self.config[Configuration.MIN_PAPERS]] * len(reviewer_ids)
            if type(self.config[Configuration.MAX_PAPERS]) == str:
                maximums = [int(self.config[Configuration.MAX_PAPERS])] * len(reviewer_ids)
            else: maximums = [self.config[Configuration.MAX_PAPERS]] * len(reviewer_ids)

            # enter 'processing' phase
            self.logger.debug("Encoding meta-data")
            # instantiate the metadata encoder, and use it to instantiate a flow solver
            encoder = Encoder(metadata, self.config, reviewer_ids)
            # The config contains custom_loads which is a dictionary where keys are user names
            # and values are max values to override the max_papers coming from the general config.
            for reviewer_id, custom_load in self.config.get(Configuration.CUSTOM_LOADS, {}).items():
                if reviewer_id in encoder.index_by_reviewer:
                    reviewer_index = encoder.index_by_reviewer[reviewer_id]
                    maximums[reviewer_index] = custom_load
                    if custom_load < minimums[reviewer_index]:
                        minimums[reviewer_index] = custom_load
            self.logger.debug("Preparing Solver")
            flow_solver = Solver(minimums, maximums, demands, encoder.cost_matrix, encoder.constraint_matrix)
            self.logger.debug("Running Solver")
            # find a solution
            solution = flow_solver.solve()
            if flow_solver.is_solved():
                # decode the solution matrix
                self.logger.debug("Decoding Solution")
                assignments_by_forum, alternates_by_forum = encoder.decode(solution)
                # put the proposed assignment in the db
                self.save_suggested_assignment(alternates_by_forum, assignment_inv, assignments_by_forum)
                self.set_status(Configuration.STATUS_COMPLETE)
            else:
                self.logger.debug('Failure: Solver could not find a solution.')
                self.set_status(Configuration.STATUS_NO_SOLUTION, 'Solver could not find a solution.  Adjust your parameters' )
        # If any exception occurs while processing we need to set the status of the config note to indicate
        # failure.
        except Exception as e:
            msg = "Internal Error while running solver: " + str(e)
            self.set_status(Configuration.STATUS_ERROR,msg)
            raise e
        else:
             return self.config_note


    # delete assignment notes created by previous runs of matcher
    def clear_existing_match(self, assignment_inv):
        notes_list = list(openreview.tools.iterget_notes(self.client, invitation=assignment_inv.id,
                                                         content = { 'label': self.config[Configuration.LABEL]}))
        for assignment_note in notes_list:
            assignment_note.ddate = round(time.time()) * 1000
            self.client.post_note(assignment_note)
        assert len(list(openreview.tools.iterget_notes(self.client, invitation=assignment_inv.id,
                                                       content = { 'label': self.config[Configuration.LABEL]}))) == 0, \
            "All assignment notes with the label " +self.config[Configuration.LABEL]+ " were not deleted!"


    # save the assignment as a set of notes.
    def save_suggested_assignment (self, alternates_by_forum, assignment_inv, assignments_by_forum):
        self.logger.debug("Clearing Existing Assignment notes")
        # clear the existing assignments from previous runs of this.
        self.clear_existing_match(assignment_inv)
        self.logger.debug("Saving New Assignment notes")
        title = self.config[Configuration.LABEL] + " Assignment Suggestion"
        # post assignments
        for forum, assignments in assignments_by_forum.items():
            alternates = alternates_by_forum.get(forum, [])
            self.client.post_note(openreview.Note.from_json({
                'forum': forum,
                'invitation': assignment_inv.id,
                'replyto': forum,
                'readers': assignment_inv.reply['readers']['values'],
                'writers': assignment_inv.reply['writers']['values'],
                'signatures': assignment_inv.reply['signatures']['values'],
                'content': {
                    Assignment.TITLE: title,
                    Assignment.ASSIGNED_GROUPS: assignments,
                    Assignment.ALTERNATE_GROUPS: alternates
                }
            }))

    # paper-reviewer-score notes should have title (per MB request) but that might have been ommited in
    # scripts that create them, so we check them and add one if nothing present.
    def _add_title (self, paper_rev_score_notes):
        title = "Reviewer Scores for " + self.config_note.content[Configuration.LABEL]
        for note in paper_rev_score_notes:
            if note.content.get(PaperReviewerScore.TITLE) == None:
                note.content[PaperReviewerScore.TITLE] = title
                self.client.post_note(note)
