import openreview
import threading
import logging
import time
from matcher.assignment_graph import AssignmentGraph, GraphBuilder
from matcher.Encoder import Encoder
from matcher.fields import Configuration
from matcher.PaperReviewerData import PaperReviewerData
from matcher.PaperUserScores import PaperUserScores
from matcher.PaperReviewerEdgeInvitationIds import PaperReviewerEdgeInvitationIds
from matcher.EdgeFetcher import EdgeFetcher


def time_ms ():
    return int(round(time.time() * 1000))

class Match:

    def __init__ (self, client, config_note, logger=logging.getLogger(__name__)):
        self.client = client
        self.config_note = config_note
        self.config = self.config_note.content
        self.logger = logger
        self.set_status(Configuration.STATUS_INITIALIZED)
        self.paper_reviewer_data = None

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


    # from notes and edges get the necessary data and keep internally
    def extract_conference_data (self):
        self.papers = list(openreview.tools.iterget_notes(self.client, invitation=self.config[Configuration.PAPER_INVITATION]))
        reviewer_group = self.client.get_group(self.config['match_group'])
        self.reviewer_ids = reviewer_group.members
        self.assignment_inv = self.client.get_invitation(self.config['assignment_invitation'])

        # a dict with keys that are score invitation ids.  Each maps to a dict that contains weight, default, translate_fn
        score_spec = self.config[Configuration.SCORES_SPECIFICATION]
        conflicts_inv_id = self.config[Configuration.CONFLICTS_INVITATION_ID]
        custom_loads_inv_id = self.config[Configuration.CUSTOM_LOAD_INVITATION_ID]
        self.num_alternates = int(self.config[Configuration.ALTERNATES]) # The number of aggregate edges to create for each paper
        edge_invitations = PaperReviewerEdgeInvitationIds(score_spec.keys(),
                                                          conflicts=conflicts_inv_id,
                                                          custom_loads=custom_loads_inv_id)
        self.paper_reviewer_data = PaperReviewerData(self.papers, self.reviewer_ids, edge_invitations, score_spec, edge_fetcher=EdgeFetcher(self.client), logger=self.logger)
        self.demands = [int(self.config[Configuration.MAX_USERS])] * len(self.papers)
        self.minimums, self.maximums = self._get_reviewer_loads(custom_loads_inv_id)

    # Compute a match of reviewers to papers and post it to the as assignment notes.
    # The config note's status field will be set to reflect completion or the variety of failures.
    def compute_match(self):
        try:
            self.set_status(Configuration.STATUS_RUNNING)
            self.extract_conference_data()
            self.logger.debug("Encoding")
            encoder = Encoder(self.paper_reviewer_data, logger=self.logger)
            graph_builder = GraphBuilder.get_builder(
                self.config.get(Configuration.OBJECTIVE_TYPE, 'SimpleGraphBuilder'))

            self.logger.debug("Preparing Graph")
            graph = AssignmentGraph(
                self.minimums,
                self.maximums,
                self.demands,
                encoder.cost_matrix,
                encoder._constraint_matrix,
                graph_builder = graph_builder
            )

            self.logger.debug("Solving Graph")
            solution = graph.solve()

            if graph.solved:
                self.logger.debug("Decoding Solution")
                assignments_by_forum = encoder.decode(solution)
                self._save_suggested_assignment(self.assignment_inv, assignments_by_forum)
                self._save_aggregate_scores(assignments_by_forum)
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
        minimums = [int(self.config[Configuration.MIN_PAPERS])] * len(self.reviewer_ids)
        maximums = [int(self.config[Configuration.MAX_PAPERS])] * len(self.reviewer_ids)
        return self._get_custom_loads(custom_load_invitation_id, minimums, maximums)

    def _get_custom_loads (self, custom_load_invitation_id, minimums, maximums):
        custom_load_edges = openreview.tools.iterget_edges(self.client, invitation=custom_load_invitation_id, limit=10000)
        for edge in custom_load_edges:
            custom_load = edge.weight
            reviewer = edge.tail
            index = self.reviewer_ids.index(reviewer)
            maximums[index] = custom_load
            if custom_load < minimums[index]:
                minimums[index] = custom_load
        return minimums, maximums

    def _save_aggregate_scores (self, assignments_by_forum):
        '''
        Saves aggregate scores (weighted sum) for a paper-reviewer as an edge.
        Will save the top N scoring reviewers for each paper where N comes from the config note alternates field.
        '''
        # Note:  If a paper recieved no scoring info for a particular user, there will be a default PaperUserScores object in the data.
        self.logger.debug("Saving aggregate score edges")
        invitation = self.client.get_invitation(self.config[Configuration.AGGREGATE_SCORE_INVITATION])
        label = self.config[Configuration.TITLE]

        edges = []
        total = 0
        for forum_id, reviewers in self.paper_reviewer_data.items():
            scores_records = list(reviewers.values())
            scores_records.sort(reverse=True)
            count = 0
            for paper_user_scores in scores_records:
                if count == self.num_alternates:
                    break
                # generate only non-assigned pairs
                if not self._is_assigned(forum_id, paper_user_scores.user, assignments_by_forum):
                    edges.append(self._build_edge(invitation, forum_id, paper_user_scores.user, paper_user_scores.aggregate_score, label))
                    count += 1
                    total += 1
        openreview.tools.post_bulk_edges(self.client, edges)
        self.logger.debug("Done saving " + str(total) + " aggregate score edges")


    def _is_assigned (self, forum_id, reviewer, assignments_by_forum):
        paper_user_scores_list = assignments_by_forum[forum_id]
        for paper_user_scores in paper_user_scores_list:
            if paper_user_scores.user == reviewer:
                return True
        return False

    def _get_values(self, invitation, property):
        return invitation.reply.get(property, {}).get('values', [])

    def _build_edge (self, invitation, forum_id, reviewer, score, label):

        return openreview.Edge(head = forum_id,
            tail = reviewer,
            weight = score,
            label = label,
            invitation = invitation.id,
            readers = self._get_values(invitation, 'readers'),
            nonreaders = self._get_values(invitation, 'nonreaders'),
            writers = self._get_values(invitation, 'writers'),
            signatures = self._get_values(invitation, 'signatures'))


    def _save_suggested_assignment (self, assignment_inv, assignments_by_forum):
        '''
        Save assignment and aggregate_score edges for pairs that are assigned.
        :param assignment_inv:
        :param assignments_by_forum:
        :return:
        '''
        self.logger.debug("Saving Edges for " + assignment_inv.id)
        ag_invitation = self.client.get_invitation(self.config[Configuration.AGGREGATE_SCORE_INVITATION])
        label = self.config[Configuration.TITLE]
        edges = []
        agg_score_edges = []
        for forum, assignments in assignments_by_forum.items():
            for paper_user_scores in assignments: #type: PaperUserScores
                score = paper_user_scores.aggregate_score
                user = paper_user_scores.user
                edges.append(self._build_edge(assignment_inv, forum, user, score, label))
                agg_score_edges.append(self._build_edge(ag_invitation, forum, user, score, label))
        openreview.tools.post_bulk_edges(self.client, edges)
        openreview.tools.post_bulk_edges(self.client, agg_score_edges)
        self.logger.debug("Done saving " + str(len(edges)) + "Assignment and Aggregate_Score Edges for " + assignment_inv.id)

