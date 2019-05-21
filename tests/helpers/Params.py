class Params:
    NUM_PAPERS = 'num_papers'
    NUM_REVIEWERS = 'num_reviewers'
    NUM_REVIEWS_NEEDED_PER_PAPER = 'reviews_needed_per_paper'
    REVIEWER_MAX_PAPERS = 'reviewer_max_papers'
    REVIEWER_MIN_PAPERS = 'reviewer_min_papers'
    CUSTOM_LOAD_CONFIG = 'custom_load_config'
    CUSTOM_LOAD_SUPPLY_DEDUCTION = 'supply_deduction'
    CUSTOM_LOAD_MAP = 'reviewer_custom_loads'
    CONSTRAINTS_CONFIG = 'constraints_config'
    CONSTRAINTS_VETOS = 'constraints_vetos'
    CONSTRAINTS_LOCKS = 'constraints_locks'
    CONFLICTS_CONFIG = 'conflicts_config'
    SCORES_CONFIG = 'scores_config'
    RANDOM_SCORE = 'random'
    FIXED_SCORE = 'fixed'
    FIXED_SCORE_VALUE = 'fixed_score_value'
    INCREMENTAL_SCORE = 'incremental'
    MATRIX_SCORE = 'matrix'
    SCORE_MATRIX = 'score_matrix'
    SCORE_INCREMENT = 'score_increment'
    SCORE_TYPE = 'type'
    OMIT_ZERO_SCORE_EDGES = 'omit_zero_score_edges'
    SCORE_NAMES_LIST = 'score_names'

    def __init__ (self, params):
        self.params = params
        self.num_papers = self.params[Params.NUM_PAPERS]
        self.num_reviewers = self.params[Params.NUM_REVIEWERS]
        self.num_reviews_needed_per_paper = self.params[Params.NUM_REVIEWS_NEEDED_PER_PAPER]
        self.reviewer_max_papers = self.params[Params.REVIEWER_MAX_PAPERS]
        self.reviewer_min_papers = self.params.get(Params.REVIEWER_MIN_PAPERS, 1)
        self.custom_load_config = self.params.get(Params.CUSTOM_LOAD_CONFIG, {})
        self.custom_load_supply_deduction = self.custom_load_config.get(Params.CUSTOM_LOAD_SUPPLY_DEDUCTION, 0)
        self.custom_load_map = self.custom_load_config.get(Params.CUSTOM_LOAD_MAP, {})
        self.constraints_config = self.params.get(Params.CONSTRAINTS_CONFIG, {})
        self.constraints_locks = self.constraints_config.get(Params.CONSTRAINTS_LOCKS, {})
        self.constraints_vetos = self.constraints_config.get(Params.CONSTRAINTS_VETOS, {})
        self.conflicts_config = self.params.get(Params.CONFLICTS_CONFIG, {})
        # default scoring is affinity=1 for every paper-reviewer
        self.scores_config = self.params.get(Params.SCORES_CONFIG,
                                             {Params.SCORE_TYPE: Params.FIXED_SCORE,
                                              Params.FIXED_SCORE_VALUE: 1,
                                              Params.OMIT_ZERO_SCORE_EDGES: False,
                                              Params.SCORE_NAMES_LIST: ['affinity']})
        self.set_other_params()

    def set_other_params (self):
        self.demand = self.num_papers * self.num_reviews_needed_per_paper
        self.theoretical_supply = self.num_reviewers * self.reviewer_max_papers
        self.actual_supply = self.theoretical_supply - self.custom_load_supply_deduction


    def print_params (self):
        print('''\n\nTesting with {} papers, {} reviewers. \nEach paper needs at least {} review(s).
Reviewer reviews max of {} paper(s).\nDemand: {} Theoretical Supply: {} Actual Supply: {}
Custom load supply deduction: {} \nLock Constraints: {}\nVeto Constraints: {} \nConflicts:{}'''.format(self.num_papers,
                     self.num_reviewers,
                     self.num_reviews_needed_per_paper,
                     self.reviewer_max_papers,
                     self.demand,
                     self.theoretical_supply,
                     self.actual_supply,
                     self.custom_load_supply_deduction,
                     self.constraints_locks,
                     self.constraints_vetos,
                     self.params.get(Params.CONFLICTS_CONFIG)
                     )
              )