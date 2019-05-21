PRECISION = 0.01

def aggregate_score_to_cost (aggregate_score):
    '''
    :param aggregate_score: the weighted sum of the paper/reviewer scores
    :return: Score converted to a cost (negative and scaled up)
    '''
    return -aggregate_score / PRECISION