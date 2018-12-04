class Configuration:
    ALTERNATES = 'alternates'
    LABEL = 'label'
    SCORES_WEIGHTS = 'scores_weights'
    SCORES_NAMES = 'scores_names'
    CONSTRAINTS = 'constraints'
    CUSTOM_LOADS = 'custom_loads'
    MAX_USERS = 'max_users'
    MIN_USERS = 'min_users'
    MAX_PAPERS = 'max_papers'
    MIN_PAPERS = 'min_papers'
    META_DATA_INVITATION = 'metadata_invitation'
    STATUS = "status"
    ERROR_MESSAGE = "error_message"
    STATUS_ERROR = "Error"
    STATUS_FAILURE = "Failure"
    STATUS_COMPLETE = "Complete"
    STATUS_RUNNING = "Running"
    STATUS_INITIALIZED = "Initialized"

class PaperReviewerScore:
    USERID = 'userid'
    ENTRIES = 'entries'
    SCORES = 'scores'
    CONFLICTS = 'conflicts'

class Assignment:
    LABEL = 'label'
    SCORES = 'scores'
    CONFLICTS = 'conflicts'
    FINAL_SCORE = 'finalScore'
    USERID = 'userId'
    ASSIGNED_GROUPS = 'assignedGroups'
    ALTERNATE_GROUPS = 'alternateGroups'