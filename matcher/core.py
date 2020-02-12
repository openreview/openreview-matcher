'''Contains core matcher functions and classes.'''
import logging
import threading

from .solvers import SolverException, MinMaxSolver, FairFlow
from .encoder import Encoder

SOLVER_MAP = {
    'MinMax' : MinMaxSolver,
    'FairFlow' : FairFlow
}

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
                num_alternates=0
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

class Matcher:
    '''Main class that coordinates an Encoder and a Solver.'''
    def __init__(
                self,
                datasource,
                solver_class,
                on_set_status=None,
                on_set_assignments=None,
                on_set_alternates=None,
                logger=logging.getLogger(__name__)
            ):

        if isinstance(datasource, dict):
            self.datasource = KeywordDatasource(**datasource)
        else:
            self.datasource = datasource

        self.logger = logger
        self.on_set_status = on_set_status if on_set_status else logger.info
        self.on_set_assignments = on_set_assignments if on_set_assignments else logger.info
        self.on_set_alternates = on_set_alternates if on_set_alternates else logger.info

        self.solution = None
        self.assignments = None
        self.alternates = None

        self.solver_class = self.__set_solver_class(solver_class)

    def __set_solver_class(self, solver_class):
        return SOLVER_MAP.get(solver_class, MinMaxSolver)

    def set_status(self, status, message=None):
        self.status = status
        self.on_set_status(status, message=message)

    def set_assignments(self, assignments):
        self.assignments = assignments
        self.on_set_assignments(assignments)

    def set_alternates(self, alternates):
        self.alternates = alternates
        self.on_set_alternates(alternates)

    def run(self):
        '''
        Compute a match of reviewers to papers and post it to the as assignment notes.
        The config note's status field will be set to reflect completion or errors.
        '''
        self.set_status('Running')

        print('Start encoding')

        encoder = Encoder(
            reviewers=self.datasource.reviewers,
            papers=self.datasource.papers,
            constraints=self.datasource.constraints,
            scores_by_type=self.datasource.scores_by_type,
            weight_by_type=self.datasource.weight_by_type
        )

        print('Preparing Solver')

        self.logger.debug('Preparing solver')

        # solver
        solver = self.solver_class(
            self.datasource.minimums,
            self.datasource.maximums,
            self.datasource.demands,
            encoder,
            logger=self.logger
        )
        try:
            self.logger.debug('Solving solver')
            solution = solver.solve()
        except SolverException as error_handle:
            self.set_status('No Solution', message=str(error_handle))

        if solver.solved:
            self.solution = solution
            self.set_assignments(encoder.decode_assignments(solution))
            self.set_alternates(
                encoder.decode_alternates(solution, self.datasource.num_alternates))
            self.set_status('Complete')

        else:
            self.set_status(
                'No Solution',
                message='Solver could not find a solution. Adjust your parameters')

