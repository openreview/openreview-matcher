import openreview
import threading
from matcher.assignment_graph import AssignmentGraph, GraphBuilder
from matcher.encoder import Encoder
from matcher.encoder2 import Encoder2
from matcher.fields import Configuration
from matcher.fields import Assignment
from Metadata import Metadata
from matcher import app
import logging
import time

def time_ms ():
    return int(round(time.time() * 1000))

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
        self.config_note = self.client.post_note(self.config_note)
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


    # Compute a match of reviewers to papers and post it to the as assignment notes.
    # The config note's status field will be set to reflect completion or the variety of failures.
    def compute_match(self):
        try:
            self.set_status(Configuration.STATUS_RUNNING)
            papers = list(openreview.tools.iterget_notes(self.client, invitation=self.config[Configuration.PAPER_INVITATION]))
            reviewer_group = self.client.get_group(self.config['match_group'])
            assignment_inv = self.client.get_invitation(self.config['assignment_invitation'])
            score_invitation_ids = self.config[Configuration.SCORES_INVITATIONS]
            score_names = self.config[Configuration.SCORES_NAMES]
            weights = self.config[Configuration.SCORES_WEIGHTS]
            reviewer_ids = reviewer_group.members
            assert len(score_invitation_ids) == score_names == weights, "The configuration note should specify the same number of scores, weights, and score-invitations"
            metadata = Metadata(self.client, papers, reviewer_ids, score_invitation_ids)
            inv_score_names = [metadata.translate_score_inv_to_score_name(inv_id) for inv_id in score_invitation_ids]
            assert set(inv_score_names) == set(score_names),  "In the configuration note, the invitations for scores must correspond to the score names"
            if type(self.config[Configuration.MAX_USERS]) == str:
                demands = [int(self.config[Configuration.MAX_USERS])] * len(papers)
            else:
                demands = [self.config[Configuration.MAX_USERS]] * len(papers)

            if type(self.config[Configuration.MIN_PAPERS]) == str:
                minimums = [int(self.config[Configuration.MIN_PAPERS])] * len(reviewer_ids)
            else:
                minimums = [self.config[Configuration.MIN_PAPERS]] * len(reviewer_ids)

            if type(self.config[Configuration.MAX_PAPERS]) == str:
                maximums = [int(self.config[Configuration.MAX_PAPERS])] * len(reviewer_ids)
            else:
                maximums = [self.config[Configuration.MAX_PAPERS]] * len(reviewer_ids)

            self.logger.debug("Encoding metadata")
            encoder = Encoder(metadata, self.config, reviewer_ids)
            # encoder = Encoder2(metadata, self.config)

            # The config contains custom_loads which is a dictionary where keys are user names
            # and values are max values to override the max_papers coming from the general config.
            for reviewer_id, custom_load in self.config.get(Configuration.CUSTOM_LOADS, {}).items():
                if reviewer_id in encoder.index_by_reviewer:
                    reviewer_index = encoder.index_by_reviewer[reviewer_id]
                    maximums[reviewer_index] = custom_load
                    if custom_load < minimums[reviewer_index]:
                        minimums[reviewer_index] = custom_load

            graph_builder = GraphBuilder.get_builder(
                self.config.get(Configuration.OBJECTIVE_TYPE, 'SimpleGraphBuilder'))

            self.logger.debug("Preparing Graph")
            graph = AssignmentGraph(
                minimums,
                maximums,
                demands,
                encoder.cost_matrix,
                encoder.constraint_matrix,
                graph_builder = graph_builder
            )

            self.logger.debug("Solving Graph")
            solution = graph.solve()

            if graph.solved:
                self.logger.debug("Decoding Solution")
                assignments_by_forum, alternates_by_forum = encoder.decode(solution)
                self.save_suggested_assignment2(alternates_by_forum, assignment_inv, assignments_by_forum)
                self.set_status(Configuration.STATUS_COMPLETE)
            else:
                self.logger.debug('Failure: Solver could not find a solution.')
                self.set_status(Configuration.STATUS_NO_SOLUTION, 'Solver could not find a solution.  Adjust your parameters' )

            return self.config_note
        except Exception as e:
            msg = "Internal Error while running solver: " + str(e)
            self.set_status(Configuration.STATUS_ERROR,msg)
            raise e



    def clear_existing_match(self, assignment_inv):
        '''
        Clears assignment notes created by previous runs of the matcher.
        '''
        notes_list = list(openreview.tools.iterget_notes(self.client, invitation=assignment_inv.id,
                                                         content = {Configuration.TITLE: self.config[Configuration.TITLE]}))
        for assignment_note in notes_list:
            assignment_note.ddate = round(time.time()) * 1000
            self.client.post_note(assignment_note)
        assert len(list(openreview.tools.iterget_notes(self.client, invitation=assignment_inv.id,
                                                       content = {Configuration.TITLE: self.config[Configuration.TITLE]}))) == 0, \
            "All assignment notes with the label " + self.config[Configuration.TITLE] + " were not deleted!"


    # save the assignment as a set of notes.
    def save_suggested_assignment(self, alternates_by_forum, assignment_inv, assignments_by_forum):
        self.logger.debug("Clearing Existing Assignment notes")
        self.clear_existing_match(assignment_inv)
        self.logger.debug("Saving New Assignment notes")

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
                    Assignment.TITLE: self.config[Configuration.TITLE],
                    Assignment.ASSIGNED_GROUPS: assignments,
                    Assignment.ALTERNATE_GROUPS: alternates
                }
            }))

    def clear_existing_match2(self, assignment_inv):
        label = self.config[Configuration.TITLE]
        assignment_edges = list(openreview.tools.iterget_edges(self.client, invitation=assignment_inv.id, label=label))
        for edge in assignment_edges:
            edge.ddate = round(time.time()) * 1000
            self.client.post_edge(edge)



    def save_suggested_assignment2 (self, alternates_by_forum, assignment_inv, assignments_by_forum):
        # self.clear_existing_match2(assignment_inv)
        label = self.config[Configuration.TITLE]
        for forum, assignments in assignments_by_forum.items():
            for entry in assignments:
                score = entry[Assignment.FINAL_SCORE]
                try:
                    e = openreview.Edge(invitation=assignment_inv.id,
                                        head=forum,
                                        tail=entry[Assignment.USERID],
                                        label=label,
                                        weight=score,
                                        readers=['everyone'],
                                        writers=['everyone'],
                                        signatures=[])
                    self.client.post_edge(e)
                except Exception as exc:
                    print(exc)
                    raise exc


