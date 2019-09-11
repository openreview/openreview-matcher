'''
CLI interface for the matcher
'''

import argparse
import csv
import json
from .core import Matcher
from .solvers import MinMaxSolver, FairFlow

parser = argparse.ArgumentParser()
parser.add_argument(
    '--scores',
    nargs='+',
    help='''
        One or more score files,
        with each row containing comma-separated paperID, userID, and score (in that order).
        e.g. "paper1,reviewer1,0.5"
        '''
)

parser.add_argument(
    '--constraints',
    nargs='*',
    help='''
        One or more constraint files,
        with each row containing comma-separated paperId, userID, and constraint (in that order).
        Constraint values must be -1 (conflict), 1 (forced assignment), or 0 (no effect).
        e.g. "paper1,reviewer1,-1"
        '''
)

parser.add_argument('--weights', nargs='+', type=int)
parser.add_argument('--min_papers', default=0, type=int)
parser.add_argument('--max_papers', type=int)
parser.add_argument('--num_reviewers', default=3, type=int)
parser.add_argument('--num_alternates', default=3, type=int)

# TODO: dynamically populate solvers list
# TODO: can argparse throw an error if the solver isn't in the list?
parser.add_argument(
    '--solver',
    help='Choose from: {}'.format(['MinMaxSolver', 'FairFlow']),
    default='MinMaxSolver'
)

args = parser.parse_args()


# Main Logic

solver_class = None
if args.solver == 'MinMaxSolver':
    solver_class = MinMaxSolver
if args.solver == 'FairFlow':
    solver_class = FairFlow

if not solver_class:
    raise ValueError('Invalid solver class {}'.format(args.solver))

reviewer_set = set()
paper_set = set()

weight_by_type = {
    score_file: args.weights[idx] for idx, score_file in enumerate(args.scores)}

scores_by_type = {score_file: [] for score_file in args.scores}
for score_file in args.scores:
    file_reviewers = []
    file_papers = []

    with open(score_file) as file_handle:

        for row in csv.reader(file_handle):
            paper_id = row[0]
            profile_id = row[1]
            score = row[2]

            file_reviewers.append(profile_id)
            file_papers.append(paper_id)
            scores_by_type[score_file].append((paper_id, profile_id, score))

    reviewer_set.update(file_reviewers)
    paper_set.update(file_papers)

constraints = []
if args.constraints:
    with open(args.constraints) as file_handle:
        for row in csv.reader(file_handle):
            paper_id = row[0]
            profile_id = row[1]
            constraint = row[2]

            reviewer_set.update([profile_id])
            paper_set.append([paper_id])

            constraints.append((paper_id, profile_id, constraint))

reviewers = sorted(list(reviewer_set))
papers = sorted(list(paper_set))

minimums = [args.min_papers] * len(reviewers)
maximums = [args.max_papers] * len(reviewers)
demands = [args.num_reviewers] * len(papers)
num_alternates = args.num_alternates

match_data = {
    'reviewers': reviewers,
    'papers': papers,
    'constraints': constraints,
    'scores_by_type': scores_by_type,
    'weight_by_type': weight_by_type,
    'minimums': minimums,
    'maximums': maximums,
    'demands': demands,
    'num_alternates': num_alternates
}

def write_assignments(assignments):
    with open('./assignments.json', 'w') as f:
        f.write(json.dumps(assignments, indent=2))

def write_alternates(alternates):
    with open('./alternates.json', 'w') as f:
        f.write(json.dumps(alternates, indent=2))

matcher = Matcher(
    datasource=match_data,
    on_set_status=print,
    on_set_assignments=write_assignments,
    on_set_alternates=write_alternates,
    solver_class=solver_class
)

matcher.run()
