import openreview
import threading
from matcher.assignment_graph import AssignmentGraph, GraphBuilder
from matcher.encoder import Encoder
from matcher.encoder2 import Encoder2
from matcher.fields import Configuration
from matcher.fields import Assignment
from matcher.Metadata import Metadata
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
            self.papers = list(openreview.tools.iterget_notes(self.client, invitation=self.config[Configuration.PAPER_INVITATION]))
            reviewer_group = self.client.get_group(self.config['match_group'])
            assignment_inv = self.client.get_invitation(self.config['assignment_invitation'])
            score_invitation_ids = self.config[Configuration.SCORES_INVITATIONS]
            score_names = self.config[Configuration.SCORES_NAMES]
            weights = self.config[Configuration.SCORES_WEIGHTS]
            self.reviewer_ids = reviewer_group.members
            metadata = Metadata(self.client, self.papers, self.reviewer_ids, score_invitation_ids, self.logger)
            inv_score_names = [metadata.translate_score_inv_to_score_name(inv_id) for inv_id in score_invitation_ids]

            # temporary stuff until I convert conflicts and constraints to edges
            md_inv = self.config['metadata_invitation']
            md_notes = list(openreview.tools.iterget_notes(self.client, invitation=md_inv))
            metadata.add_conflicts(md_notes)
            metadata.add_constraints(self.config[Configuration.CONSTRAINTS])
            #end temp stuff

            assert set(inv_score_names) == set(score_names),  "In the configuration note, the invitations for scores must correspond to the score names"
            if type(self.config[Configuration.MAX_USERS]) == str:
                demands = [int(self.config[Configuration.MAX_USERS])] * len(self.papers)
            else:
                demands = [self.config[Configuration.MAX_USERS]] * len(self.papers)

            if type(self.config[Configuration.MIN_PAPERS]) == str:
                minimums = [int(self.config[Configuration.MIN_PAPERS])] * len(self.reviewer_ids)
            else:
                minimums = [self.config[Configuration.MIN_PAPERS]] * len(self.reviewer_ids)

            if type(self.config[Configuration.MAX_PAPERS]) == str:
                maximums = [int(self.config[Configuration.MAX_PAPERS])] * len(self.reviewer_ids)
            else:
                maximums = [self.config[Configuration.MAX_PAPERS]] * len(self.reviewer_ids)

            self.logger.debug("Encoding metadata")
            # encoder = Encoder(metadata, self.config, reviewer_ids, logger=self.logger)
            encoder = Encoder(metadata, self.config, self.reviewer_ids, logger=self.logger)

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
                encoder._cost_matrix,
                encoder.constraint_matrix,
                graph_builder = graph_builder
            )

            self.logger.debug("Solving Graph")
            solution = graph.solve()

            if graph.solved:
                self.logger.debug("Decoding Solution")
                assignments_by_forum, alternates_by_forum = encoder.decode(solution)
                self.save_suggested_assignment(alternates_by_forum, assignment_inv, assignments_by_forum)
                self.save_aggregate_scores2(encoder, metadata)
                self.set_status(Configuration.STATUS_COMPLETE)
            else:
                self.logger.debug('Failure: Solver could not find a solution.')
                self.set_status(Configuration.STATUS_NO_SOLUTION, 'Solver could not find a solution.  Adjust your parameters' )

            return self.config_note
        except Exception as e:
            msg = "Internal Error while running solver: " + str(e)
            self.set_status(Configuration.STATUS_ERROR,msg)
            raise e

    def save_aggregate_scores2 (self, encoder, metadata):
        '''
        Saves aggregate scores (weighted sum) for each paper-reviewer as an edge.
        :param encoder:
        :return:
        '''
        aggregate_inv_id = self.config[Configuration.AGGREGATE_SCORE_INVITATION]
        edges = []
        for forum_id, reviewers in metadata.entries_by_forum_map.items():
            for reviewer, entry in reviewers.items():
                ag_score = encoder.cost_function.aggregate_score(entry,encoder.weights)
                e = openreview.Edge(head=forum_id, tail=reviewer, weight=ag_score, invitation=aggregate_inv_id,
                                    readers=['everyone'], writers=[self.config[Configuration.CONFIG_INVITATION_ID]], signatures=[reviewer])
                edges.append(e)
        self.client.post_bulk_edges(edges)


    def save_aggregate_scores (self, encoder):
        '''
        An alternative to the above which builds the aggregate score edges using the encoder's cost-matrix.
        The reason this is problematic is that the cost-matrix holds COSTS and not scores.   These costs are negative floats
        that have been scaled up from the scores using a cost-function object.   This uses that cost function object to reverse the
        process and convert the cost back into a score but it loses a little bit of floating point precision in so doing.   It's negligible
        but a unit test then has to do rounding in order for the verification and the above save_aggregate_scores2 because it turns the raw
        score data into an aggregate.
        :param encoder:
        :return:
        '''
        aggregate_inv_id = self.config[Configuration.AGGREGATE_SCORE_INVITATION]
        edges = []
        cost_matrix = encoder.cost_matrix
        num_reviewers, num_papers = cost_matrix.shape
        for r_ix in range(num_reviewers):
            for p_ix in range(num_papers):
                paper = self.papers[p_ix]
                reviewer = self.reviewer_ids[r_ix]
                val = encoder.cost_function.cost_to_aggregate_score(cost_matrix[r_ix,p_ix])
                e = openreview.Edge(head=paper.id, tail=reviewer, weight=val, invitation=aggregate_inv_id,
                                    readers=['everyone'], writers=[self.config[Configuration.CONFIG_INVITATION_ID]], signatures=[reviewer])
                edges.append(e)
        self.client.post_bulk_edges(edges)

    def clear_existing_match(self, assignment_inv):
        self.logger.debug("Clearing Existing Edges for " + assignment_inv.id)
        label = self.config[Configuration.TITLE]
        assignment_edges = openreview.tools.iterget_edges(self.client, invitation=assignment_inv.id, label=label, limit=10000)
        edges = []
        # change all the assignment-edges
        for edge in assignment_edges:
            edge.ddate = round(time.time()) * 1000
            edges.append(edge)
        # post them all back in bulk
        self.client.post_bulk_edges(edges)
        self.logger.debug("Done clearing Existing Edges for " + assignment_inv.id)


    # TODO nothing is being done with alternates
    def save_suggested_assignment (self, alternates_by_forum, assignment_inv, assignments_by_forum):
        # self.clear_existing_match(assignment_inv)
        self.logger.debug("Saving Edges for " + assignment_inv.id)
        label = self.config[Configuration.TITLE]
        edges = []
        for forum, assignments in assignments_by_forum.items():
            for entry in assignments:
                score = entry[Assignment.FINAL_SCORE]
                e = openreview.Edge(invitation=assignment_inv.id,
                                    head=forum,
                                    tail=entry[Assignment.USERID],
                                    label=label,
                                    weight=score,
                                    readers=['everyone'],
                                    writers=['everyone'],
                                    signatures=[])
                edges.append(e)
        self.client.post_bulk_edges(edges) # bulk posting of edges is much faster than individually
        self.logger.debug("Done saving " + str(len(edges)) + " Edges for " + assignment_inv.id)



