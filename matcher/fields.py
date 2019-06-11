class Configuration:
    ALTERNATES = 'alternates'
    TITLE = 'title'
    SCORES_SPECIFICATION = 'scores_specification'
    SCORE_WEIGHT = 'weight'
    SCORE_DEFAULT = 'default'
    SCORE_TRANSLATE_FN = 'translate_fn'
    SCORE_TRANSLATE_MAP = 'translate_map'
    CONSTRAINTS = 'constraints'
    CUSTOM_LOADS = 'custom_loads'
    MAX_USERS = 'max_users'
    MIN_USERS = 'min_users'
    MAX_PAPERS = 'max_papers'
    MIN_PAPERS = 'min_papers'
    STATUS = "status"
    ERROR_MESSAGE = "error_message"
    STATUS_ERROR = "Error"
    STATUS_NO_SOLUTION = "No Solution"
    STATUS_COMPLETE = "Complete"
    STATUS_RUNNING = "Running"
    STATUS_INITIALIZED = "Initialized"
    OBJECTIVE_TYPE = "objective_type"
    LOCK = '+inf'
    VETO = '-inf'
    PAPER_INVITATION = "paper_invitation"
    AGGREGATE_SCORE_INVITATION = "aggregate_score_invitation"
    CONFIG_INVITATION_ID = "config_invitation"
    CUSTOM_LOAD_INVITATION_ID = "custom_load_invitation"
    CONSTRAINTS_INVITATION_ID = "constraints_invitation"
    CONFLICTS_INVITATION_ID = "conflicts_invitation"


class PaperReviewerScore:
    USERID = 'userid'
    ENTRIES = 'entries'
    SCORES = 'scores'
    CONFLICTS = 'conflicts'

class Assignment:
    TITLE = 'title'
    SCORES = 'scores'
    CONFLICTS = 'conflicts'
    FINAL_SCORE = 'finalScore'
    USERID = 'userId'
    ASSIGNED_GROUPS = 'assignedGroups'
    ALTERNATE_GROUPS = 'alternateGroups'