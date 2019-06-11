def translate_score_inv_to_score_name (score_inv_id):
    score_name = score_inv_id.split('/')[-1]  # like bid, tpms, subjectArea
    return score_name