import openreview
import threading
from matcher.solver import Solver
from matcher.encoder import Encoder
import logging

class Match:

    STATUS_ERROR = "Error"
    STATUS_FAILURE = "Failure"
    STATUS_COMPLETE = "Complete"
    STATUS_RUNNING = "Running"
    STATUS_INITIALIZED = "Initialized"

    def __init__ (self, client, config_note, logger=logging.getLogger(__name__)):
        self.client = client
        self.config_note = config_note
        self.config = self.config_note.content
        self.logger = logger
        self.set_status(Match.STATUS_INITIALIZED)

    def set_status (self, status, message=None):
        statmsg = status + (': ' + message if message else '')
        self.config_note.content['status'] = statmsg
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
            self.set_status(Match.STATUS_RUNNING)
            metadata = list(openreview.tools.iterget_notes(self.client, invitation=self.config['metadata_invitation']))
            reviewer_group = self.client.get_group(self.config['match_group'])
            paper_notes = list(openreview.tools.iterget_notes(self.client, invitation=self.config['paper_invitation']))
            assert len(paper_notes) == len(metadata), "There is a difference between meta-data size and number of papers"
            assignment_inv = self.client.get_invitation(self.config['assignment_invitation'])
            reviewer_ids = reviewer_group.members
            md_reviewers = metadata[0].content['entries'] if len(metadata) > 0 else []
            md_revs_size = len(md_reviewers)
            group_size = len(reviewer_ids)
            assert md_revs_size == group_size, "The number of reviewers in a meta-data note is different from the number of reviewers in the conference reviewers group"
            # This could be set by hand if reviewers or papers have specific supplies/demands
            supplies = [self.config['max_papers']] * len(reviewer_ids)
            demands = [self.config['max_users']] * len(metadata)
            minimums = [self.config['min_papers']] * len(reviewer_ids)
            maximums = [self.config['max_papers']] * len(reviewer_ids)

            # enter 'processing' phase
            self.logger.debug("Clearing Existing Assignment notes")
            # clear the existing assignments from previous runs of this.
            self.clear_existing_match(assignment_inv)
            self.logger.debug("Encoding meta-data")
            # instantiate the metadata encoder, and use it to instantiate a flow solver
            encoder = Encoder(metadata, self.config, reviewer_ids)
            # The config contains custom_loads which is a dictionary where keys are user names
            # and values are max values to override the max_papers coming from the general config.
            for reviewer_id, custom_load in self.config.get('custom_loads',{}).items():
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
                self.logger.debug("Saving Assignment notes")
                self.save_suggested_assignment(alternates_by_forum, assignment_inv, assignments_by_forum)
                self.set_status(Match.STATUS_COMPLETE)
            else:
                self.logger.debug('Failure: Solver could not find a solution.')
                self.set_status(Match.FAILURE, 'Solver could not find a solution.  Adjust your parameters' )
        # If any exception occurs while processing we need to set the status of the config note to indicate
        # failure.
        except Exception as e:
            msg = "Internal Error while running solver: " + str(e)
            self.set_status(Match.STATUS_ERROR,msg)
            raise e
        else:
             return self.config_note


    # delete assignment notes created by previous runs of matcher
    def clear_existing_match(self, assignment_inv):
        for assignment_note in openreview.tools.iterget_notes(self.client, invitation=assignment_inv.id):
            if assignment_note.content['label'] == self.config['label']:
                self.client.delete_note(assignment_note)


    # save the assignment as a set of notes.
    def save_suggested_assignment (self, alternates_by_forum, assignment_inv, assignments_by_forum):
        # post assignments
        for forum, assignments in assignments_by_forum.items():
            alternates = alternates_by_forum[forum]
            self.client.post_note(openreview.Note.from_json({
                'forum': forum,
                'invitation': assignment_inv.id,
                'replyto': forum,
                'readers': assignment_inv.reply['readers']['values'],
                'writers': assignment_inv.reply['writers']['values'],
                'signatures': assignment_inv.reply['signatures']['values'],
                'content': {
                    'label': self.config['label'],
                    'assignedGroups': assignments,
                    'alternateGroups': alternates
                }
            }))
