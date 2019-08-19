'''
Main class that coordinates an Encoder and a Solver.

Uses a MatcherClient to communicate with the OpenReview server instance.

'''
import logging
import threading

from .solvers import MinMaxSolver
from .encoder import Encoder

class MatcherError(Exception):
    '''Exception wrapper class for errors related to Matcher'''
    pass

class Matcher:
    '''
    TODO
    '''
    def __init__(self, client, config, logger=logging.getLogger(__name__)):
        self.client = client
        self.config = config
        self.logger = logger

        self.client.set_status('Initialized')

        self.num_alternates = int(self.config['alternates'])
        self.demands = [int(self.config['max_users']) for paper in self.client.papers]
        self.minimums, self.maximums = self._get_quota_arrays()

        self.solution = None

    def compute_match(self):
        '''
        Compute a match of reviewers to papers and post it to the as assignment notes.
        The config note's status field will be set to reflect completion or errors.
        '''
        # try:
        self.client.set_status('Running')

        encoder = Encoder(
            self.client.reviewers,
            self.client.papers,
            self.client.constraint_edges,
            self.client.edges_by_invitation,
            self.config['scores_specification'])

        self.logger.debug('Preparing solver')

        solver = MinMaxSolver(
            self.minimums,
            self.maximums,
            self.demands,
            encoder.cost_matrix,
            encoder.constraint_matrix
        )

        self.logger.debug('Solving solver')
        solution = solver.solve()

        if solver.solved:
            self.solution = solution

            assignments_by_forum = encoder.assignments(solution)
            self.client.save_suggested_assignments(assignments_by_forum)

            alternates_by_forum = encoder.alternates(solution, self.num_alternates)
            self.client.save_suggested_alternates(alternates_by_forum)

            self.client.set_status('Complete')
        else:
            self.client.set_status(
                'No solution',
                'Solver could not find a solution. Adjust your parameters')

    def run_thread(self):
        '''thread executor for compute_match function'''
        thread = threading.Thread(target=self.compute_match)
        thread.start()

    def _get_quota_arrays(self):
        '''get `minimum` and `maximum` reviewer load arrays, accounting for custom loads'''
        minimums = [int(self.config['min_papers']) for r in self.client.reviewers]
        maximums = [int(self.config['max_papers']) for r in self.client.reviewers]

        for edge in self.client.custom_load_edges:
            try:
                custom_load = int(edge.weight)
            except ValueError:
                raise MatcherError('invalid custom load weight')

            if custom_load < 0:
                custom_load = 0

            index = self.client.reviewers.index(edge.tail)
            maximums[index] = custom_load

            if custom_load < minimums[index]:
                minimums[index] = custom_load

        return minimums, maximums
