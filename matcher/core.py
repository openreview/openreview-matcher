'''Contains core matcher functions and classes.'''
import logging
import threading
import time
import json
from enum import Enum
from .solvers import SolverException, MinMaxSolver, FairFlow
from .encoder import Encoder

SOLVER_MAP = {
    'MinMax' : MinMaxSolver,
    'FairFlow' : FairFlow
}

class MATCHER_STATUS(Enum):
    INITIALIZED = 'Initialized'
    RUNNING = 'Running'
    ERROR = 'Error'
    NO_SOLUTION = 'No Solution'
    COMPLETE = "Complete"
    DEPLOYED = "Deployed"

class MatcherError(Exception):
    '''Exception wrapper class for errors related to Matcher.'''
    pass

class KeywordDatasource:
    def __init__(
                self,
                reviewers=[],
                papers=[],
                constraints=[],
                scores_by_type=None,
                weight_by_type=None,
                minimums=[],
                maximums=[],
                demands=[],
                num_alternates=0,
                assignments_output='assignments.json',
                alternates_output='alternates.json',
                logger=logging.getLogger(__name__)
            ):

        self.reviewers = reviewers
        self.papers = papers
        self.constraints = constraints
        self.scores_by_type = scores_by_type if scores_by_type else {}
        self.weight_by_type = weight_by_type if weight_by_type else {}
        self.minimums = minimums
        self.maximums = maximums
        self.demands = demands
        self.num_alternates = num_alternates
        self.normalization_types = []
        self.assignments_output = assignments_output
        self.alternates_output = alternates_output
        self.logger = logger

    def set_assignments(self, assignments):
        self.logger.info('Writing assignments to file')
        with open(self.assignments_output, 'w') as f:
            f.write(json.dumps(assignments, indent=2))

    def set_alternates(self, alternates):
        self.logger.info('Writing alternates to file')
        with open(self.alternates_output, 'w') as f:
            f.write(json.dumps(alternates, indent=2))

    def set_status(self, status, message):
        self.logger.info('status={0}, message={1}'.format(status.value, message))

class Matcher:
    '''Main class that coordinates an Encoder and a Solver.'''
    def __init__(
                self,
                datasource,
                solver_class,
                on_set_status=None,
                logger=logging.getLogger(__name__)
            ):

        if isinstance(datasource, dict):
            self.datasource = KeywordDatasource(**datasource)
        else:
            self.datasource = datasource

        self.logger = logger
        self.solution = None
        self.assignments = None
        self.alternates = None

        self.solver_class = self.__set_solver_class(solver_class)

    def __set_solver_class(self, solver_class):
        return SOLVER_MAP.get(solver_class, MinMaxSolver)

    def set_status(self, status, message=None):
        self.status = status.value
        self.datasource.set_status(status, message=message)

    def set_assignments(self, assignments):
        self.assignments = assignments
        self.datasource.set_assignments(assignments)

    def set_alternates(self, alternates):
        self.alternates = alternates
        self.datasource.set_alternates(alternates)

    def run(self):
        '''
        Compute a match of reviewers to papers and post it to the as assignment notes.
        The config note's status field will be set to reflect completion or errors.
        '''
        self.set_status(MATCHER_STATUS.RUNNING)

        self.logger.debug('Start encoding')

        encoder = Encoder(
            reviewers=self.datasource.reviewers,
            papers=self.datasource.papers,
            constraints=self.datasource.constraints,
            scores_by_type=self.datasource.scores_by_type,
            weight_by_type=self.datasource.weight_by_type,
            normalization_types=self.datasource.normalization_types,
            logger=self.logger
        )

        self.logger.debug('Preparing solver')

        # solver
        solver = self.solver_class(
            self.datasource.minimums,
            self.datasource.maximums,
            self.datasource.demands,
            encoder,
            logger=self.logger
        )

        solution = None
        start_time = time.time()

        try:
            self.logger.debug('Solving solver')
            solution = solver.solve()
        except SolverException as error_handle:
            self.logger.debug('No Solution={}'.format(error_handle))
            self.set_status(MATCHER_STATUS.NO_SOLUTION, message=str(error_handle))

        self.logger.debug('Complete solver run took {} seconds'.format(time.time() - start_time))
        if solver.solved:
            self.solution = solution
            self.set_assignments(encoder.decode_assignments(solution))
            self.set_alternates(
                encoder.decode_alternates(solution, self.datasource.num_alternates))
            self.set_status(MATCHER_STATUS.COMPLETE)
