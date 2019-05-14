import openreview
import threading
import logging
import time
from matcher.assignment_graph import AssignmentGraph, GraphBuilder
from matcher.Encoder import Encoder
from matcher.fields import Configuration
from matcher.fields import Assignment
from matcher.PaperReviewerInfo import PaperReviewerInfo
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds


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
            conflicts_inv_id = self.config[Configuration.CONFLICTS_INVITATION_ID]
            constraints_inv_id = self.config[Configuration.CONSTRAINTS_INVITATION_ID]
            custom_loads_inv_id = self.config[Configuration.CUSTOM_LOAD_INVITATION_ID]
            edge_invitations = PaperReviewerEdgeInvitationIds(score_invitation_ids,
                                                            conflicts=conflicts_inv_id,
                                                            constraints=constraints_inv_id,
                                                            custom_loads=custom_loads_inv_id)
            paper_reviewer_info = PaperReviewerInfo(self.client, self.config[Configuration.TITLE], self.papers, self.reviewer_ids, edge_invitations, self.logger)
            inv_score_names = [paper_reviewer_info.translate_score_inv_to_score_name(inv_id) for inv_id in score_invitation_ids]
            assert set(inv_score_names) == set(score_names),  "In the configuration note, the invitations for scores must correspond to the score names"
            if type(self.config[Configuration.MAX_USERS]) == str:
                demands = [int(self.config[Configuration.MAX_USERS])] * len(self.papers)
            else:
                demands = [self.config[Configuration.MAX_USERS]] * len(self.papers)

            self.logger.debug("Encoding")
            encoder = Encoder(paper_reviewer_info, self.config, logger=self.logger)
            minimums, maximums = self._get_reviewer_loads(custom_loads_inv_id)


            graph_builder = GraphBuilder.get_builder(
                self.config.get(Configuration.OBJECTIVE_TYPE, 'SimpleGraphBuilder'))

            self.logger.debug("Preparing Graph")
            graph = AssignmentGraph(
                minimums,
                maximums,
                demands,
                encoder.cost_matrix,
                encoder._constraint_matrix,
                graph_builder = graph_builder
            )

            self.logger.debug("Solving Graph")
            solution = graph.solve()

            if graph.solved:
                self.logger.debug("Decoding Solution")
                assignments_by_forum = encoder.decode(solution)
                self._save_suggested_assignment(assignment_inv, assignments_by_forum)
                self._save_aggregate_scores(encoder, paper_reviewer_info)
                self.set_status(Configuration.STATUS_COMPLETE)
            else:
                self.logger.debug('Failure: Solver could not find a solution.')
                self.set_status(Configuration.STATUS_NO_SOLUTION, 'Solver could not find a solution.  Adjust your parameters' )

            return self.config_note
        except Exception as e:
            msg = "Internal Error while running solver: " + str(e)
            self.set_status(Configuration.STATUS_ERROR,msg)
            raise e

    def _get_reviewer_loads (self, custom_load_invitation_id):
        if type(self.config[Configuration.MIN_PAPERS]) == str:
            minimums = [int(self.config[Configuration.MIN_PAPERS])] * len(self.reviewer_ids)
        else:
            minimums = [self.config[Configuration.MIN_PAPERS]] * len(self.reviewer_ids)
        if type(self.config[Configuration.MAX_PAPERS]) == str:
            maximums = [int(self.config[Configuration.MAX_PAPERS])] * len(self.reviewer_ids)
        else:
            maximums = [self.config[Configuration.MAX_PAPERS]] * len(self.reviewer_ids)

        return self._get_custom_loads(custom_load_invitation_id, minimums, maximums)

    def _get_custom_loads (self, custom_load_invitation_id, minimums, maximums):
        custom_load_edges = openreview.tools.iterget_edges(self.client, invitation=custom_load_invitation_id, head=self.config[Configuration.CONFIG_INVITATION_ID], limit=10000)
        for edge in custom_load_edges:
            custom_load = edge.weight
            reviewer = edge.tail
            index = self.reviewer_ids.index(reviewer)
            maximums[index] = custom_load
            if custom_load < minimums[index]:
                minimums[index] = custom_load
        return minimums, maximums

    def _create_reviewers_scored_map (self):
        return {r: False for r in self.reviewer_ids}

    def _save_aggregate_scores (self, encoder, paper_reviewer_info):
        '''
        Saves aggregate scores (weighted sum) for each paper-reviewer as an edge.
        '''
        # Note:  If a paper recieved no scoring info for a particular user, there will be no data in the PaperReviewerInfo object about
        # that paper/reviewer and a default aggregate score of 0 will be emitted.
        edges = []
        for forum_id, reviewers in paper_reviewer_info.items():
            reviewers_scored_map = self._create_reviewers_scored_map() # map of flags
            for reviewer, entry in reviewers.items():
                reviewers_scored_map[reviewer] = True # remember the ones that have score data.
                ag_score = encoder.cost_function.aggregate_score(entry,encoder.weights)
                edges.append(self._build_aggregate_edge(forum_id, reviewer, ag_score))
            # produce the default aggregate scores for the paper/reviewers that had no scoring data given
            for reviewer, is_scored in reviewers_scored_map.items():
                if not is_scored:
                    edges.append(self._build_aggregate_edge(forum_id, reviewer, 0.0))

        self.logger.debug("Saving " + str(len(edges)) + " aggregate score edges")
        self.client.post_bulk_edges(edges)

    def _build_aggregate_edge (self, forum_id, reviewer, agg_score):
        aggregate_inv_id = self.config[Configuration.AGGREGATE_SCORE_INVITATION]
        conf_inv_id = self.config[Configuration.CONFIG_INVITATION_ID]
        return openreview.Edge(head=forum_id, tail=reviewer, weight=agg_score, invitation=aggregate_inv_id,
                            readers=['everyone'], writers=[conf_inv_id], signatures=[reviewer])


    def _save_suggested_assignment (self, assignment_inv, assignments_by_forum):
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



