"""A module for paper-reviewer assignment solvers"""

from .core import SolverException
from .minmax_solver import MinMaxSolver
from .simple_solver import SimpleSolver
from .randomized_solver import RandomizedSolver
from .fairflow import FairFlow
from .fairsequence import FairSequence
from .fairir import FairIR
from .perturbed_maximization_solver import PerturbedMaximizationSolver