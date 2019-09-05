'''
Verifies that custom loads are being used correctly in the matcher.

'''

import itertools
import random

import pytest

from matcher import Matcher

def test_matcher_basic():
    reviewers = ['reviewer1', 'reviewer2', 'reviewer3']
    papers = ['paper1', 'paper2', 'paper3']

    scores = [
        (paper, reviewer, random.random()) \
        for paper, reviewer in itertools.product(papers, reviewers)
    ]

    minimums = [1, 1, 1]
    maximums = [1, 1, 1]
    demands = [1, 1, 1]

    test_matcher = Matcher(
        {
            'reviewers': reviewers,
            'papers': papers,
            'scores_by_type': {'affinity': scores},
            'weight_by_type': {'affinity': 1},
            'minimums': minimums,
            'maximums': maximums,
            'demands': demands,
            'num_alternates': 1
        }
    )

    test_matcher.run()

    assert test_matcher.solution.any()
    assert test_matcher.assignments
    assert test_matcher.alternates

