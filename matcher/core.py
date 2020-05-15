'''Contains core matcher functions and classes.'''
import logging
import threading
import time
from .solvers import SolverException, MinMaxSolver, FairFlow
from .encoder import Encoder
import openreview

SOLVER_MAP = {
    'MinMax' : MinMaxSolver,
    'FairFlow' : FairFlow
}

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
        self.normalization_types = []

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

        self.logger.debug('Start encoding')

        try:
            encoder = Encoder(
                reviewers=self.datasource.reviewers,
                papers=self.datasource.papers,
                constraints=self.datasource.constraints,
                scores_by_type=self.datasource.scores_by_type,
                weight_by_type=self.datasource.weight_by_type,
                normalization_types=self.datasource.normalization_types,
                logger=self.logger
            )
            self.logger.debug('Finished encoding')

        except Exception as error_handle:
            self.set_status('Error', str(error_handle))
            raise error_handle

        try:
            self.logger.debug('Preparing solver')
            solver = self.solver_class(
                self.datasource.minimums,
                self.datasource.maximums,
                self.datasource.demands,
                encoder,
                logger=self.logger
            )
            solution = None
            start_time = time.time()

            self.logger.debug('Solving solver')
            solution = solver.solve()
            self.logger.debug('Complete solver run took {} seconds'.format(time.time() - start_time))

        except SolverException as error_handle:
            self.logger.debug('No Solution={}'.format(error_handle))
            self.set_status('No Solution', message=str(error_handle))
            raise error_handle

        except Exception as error_handle:
            self.logger.debug('Error, message={}'.format(error_handle))
            self.set_status('Error', message=str(error_handle))
            raise error_handle

        if solver.solved:
            try:
                self.solution = solution
                self.logger.debug('Setting assignments')
                self.set_assignments(encoder.decode_assignments(solution))
                self.logger.debug('Finished setting assignments')
                self.logger.debug('Setting alternates')
                self.set_alternates(encoder.decode_alternates(solution, self.datasource.num_alternates))
                self.logger.debug('Finished setting alternates')
                self.set_status('Complete')
            except Exception as error_handle:
                self.set_status('Error', str(error_handle))
                raise error_handle
