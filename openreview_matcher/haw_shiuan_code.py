""" Haw Shiuan code to calculate the loss against two vectors """

import numpy as np
import random
import json

def one_side_loss(hist_parent_s, hist_child_s):
    loss_parent = 0
    total_count_parent = np.sum(hist_parent_s.values())
    for ind in hist_parent_s:
        hist_parent_i = hist_parent_s[ind]
        if (ind not in hist_child_s):
            hist_child_i = 0
            continue
        hist_child_i = hist_child_s[ind]
        hist_diff_i = hist_parent_i - hist_child_i
        if (hist_diff_i > 0):
            loss_parent += hist_diff_i
    if(total_count_parent>0):
        out = loss_parent / float(total_count_parent)
    else:
        out = 1
    return out


def order_loss_raw(hist_parent_s, hist_child_s, over_penalty):
    loss_parent_norm = one_side_loss(hist_parent_s, hist_child_s)
    loss_child_norm = one_side_loss(hist_child_s, hist_parent_s)
    loss = over_penalty * loss_child_norm + loss_parent_norm
    return loss


def compute_loss(prob_parent_s, prob_child_s, sol_a, over_penalty):
    loss = 0
    for ind in prob_parent_s:
        prob_parent_i = prob_parent_s[ind]
        if (ind not in prob_child_s):
            loss += prob_parent_i
            continue
        prob_child_i = prob_child_s[ind]
        prob_diff_i = prob_parent_i - prob_child_i * sol_a
        if (prob_diff_i > 0):
            loss += prob_diff_i
        else:
            loss -= over_penalty * prob_diff_i
    return loss


def solve_LP_by_sort(prob_child_s, prob_parent_s, over_penalty):
    poss_a_prob = []
    poss_a_0 = []
    poss_a_0_sum = 0
    target_value = 1 / float(over_penalty + 1)
    for ind in prob_child_s:
        if (ind not in prob_parent_s):
            poss_a_0.append((0, prob_child_s[ind]))
            poss_a_0_sum += prob_child_s[ind]
        else:
            poss_a = prob_parent_s[ind] / prob_child_s[ind]
            poss_a_prob.append((poss_a, prob_child_s[ind]))
    if (poss_a_0_sum >= target_value or len(poss_a_prob) == 0):
        return 1, 0
    target_value_remain = target_value - poss_a_0_sum
    poss_a_prob_sorted = sorted(poss_a_prob, key=lambda x: x[0])

    prob_sum = 0
    for j in range(len(poss_a_prob_sorted)):
        over_index = j
        prob_sum += poss_a_prob_sorted[j][1]
        if (prob_sum >= target_value_remain):
            break
    sol_a = poss_a_prob_sorted[over_index][0]
    loss = compute_loss(prob_parent_s, prob_child_s, sol_a, over_penalty)

    if (over_index > 0):
        sol_a_2 = poss_a_prob_sorted[over_index - 1][0]
        loss_2 = compute_loss(prob_parent_s, prob_child_s, sol_a_2, over_penalty)
        if (loss_2 < loss):
            loss = loss_2
            sol_a = sol_a_2
    return loss, sol_a


def compute_prob_ent(sBoW_dict):
    total_count = float(sum(sBoW_dict.values()))
    prob_dict = {}
    prob_list = []
    for ind in sBoW_dict:
        prob_i = sBoW_dict[ind] / total_count
        prob_dict[ind] = prob_i
        prob_list.append(prob_i)

    prob_np = np.array(prob_list)
    ent = -np.sum(prob_np * np.log(prob_np))

    return ent, prob_dict


def get_ent_prob(child_ind, w_d2_cache, neighbor_w):
    if (child_ind in w_d2_cache):
        ent_child, prob_child, child_nei = w_d2_cache[child_ind]
    else:
        # child_ind = w_d2_ind[child]
        child_nei = neighbor_w[child_ind]
        ent_child, prob_child = compute_prob_ent(child_nei)
        w_d2_cache[child_ind] = [ent_child, prob_child, child_nei]
    return ent_child, prob_child, child_nei


def compute_CDE(prob_child, prob_parent):
    inter_sum = 0
    norm_sum = 0
    for w in prob_child:
        norm_sum += prob_child[w]
        if (w in prob_parent):
            inter_sum += min(prob_child[w], prob_parent[w])
    if(norm_sum > 0 ):
        CDE_score = inter_sum / float(norm_sum)
    else:
        CDE_score = 0

    return CDE_score


def load_entropy_file(f_in):
    w_ind_and_ent = json.load(f_in)
    w_ind_d2_ent = {w_ind: v for w_ind, v in w_ind_and_ent}
    return w_ind_d2_ent


def compute_nei_ent(w_ind_d2_ent,child_nei,top_neighbor_k):
    child_nei_sorted = sorted(child_nei.items(), key=lambda x:x[1], reverse=True)
    ent_list=[]
    for i in range( min(top_neighbor_k, len(child_nei_sorted)) ):
        w_ind, freq = child_nei_sorted[i]
        ent_list.append(w_ind_d2_ent[w_ind])
    E_child = np.median(ent_list)
    return E_child


def compute_SLQS_sub(w_ind_d2_ent, child_nei, parent_nei):
    top_neighbor_k=100
    E_child = compute_nei_ent(w_ind_d2_ent, child_nei, top_neighbor_k)
    E_parent = compute_nei_ent(w_ind_d2_ent, parent_nei, top_neighbor_k)
    SLQS_sub = E_parent - E_child
    return SLQS_sub


def compute_method_scores(eval_data, w_d2_ind, neighbor_w, is_hyper_rel, word2vec_model, w_ind_d2_ent):
    over_penalty_1 = 5
    over_penalty_2 = 20
    oov_list = []
    result_list = []
    w_d2_cache = {}
    spec_correct = {"order_diff": [], "order_diff_s_w": [], "order_raw_diff": [], "entropy_diff": [], "CDE_diff": [],
                    "SLQS_sub": []}

    method_list = ["invCL", "CDE", "CDE norm", "entropy_order", "order_diff", "order",
                   "order_diff_small_w", "order_small_w", "entropy_diff", "order_raw",
                   "order_raw_smaller_w", "word2vec", "word2vec_entropy", "invOrder", "rnd",
                   "CDE_diff", "SLQS_sub", "order_word2vec_entropy"]

    # method_ind_map = {"invCL": 4, "CDE": 5, "CDE norm": 6, "entropy_order": 7, "order_diff": 8, "order": 9,
    #                   "order_diff_small_w": 10, "order_small_w": 11, "entropy_diff": 12, "order_raw": 13,
    #                   "order_raw_smaller_w": 14, "word2vec": 15, "word2vec_entropy": 16, "invOrder": 17, "rnd": 18,
    #                   "CDE_diff": 19,"SLQS_sub": 20, "order_word2vec_entropy": 21}
    method_ind_map = {m: 3 + i for i, m in enumerate(method_list)}

    print "computing distances"
    for i, data_i in enumerate(eval_data):
        #child, parent, pos, rel, score = data_i
        #child, parent, is_hyper, rel = data_i
        child = data_i[0]
        parent = data_i[1]
        rel = data_i[3]
        # print w_d2_ind[child]

        if len(w_d2_ind)==0:
            child_ind = child
            parent_ind = parent
        else:
            if (child not in w_d2_ind or parent not in w_d2_ind):
                oov_list.append(data_i)
                continue
            child_ind = str(w_d2_ind[child])
            parent_ind = str(w_d2_ind[parent])

        if (child_ind not in neighbor_w or parent_ind not in neighbor_w):
            oov_list.append(data_i)
            continue

        if len(w_ind_d2_ent)>0:
        #if (not use_hist_emb):
            SLQS_sub = compute_SLQS_sub(w_ind_d2_ent, neighbor_w[child_ind], neighbor_w[parent_ind])
        else:
            SLQS_sub = 0

        ent_child, prob_child, hist_child = get_ent_prob(child_ind, w_d2_cache, neighbor_w)
        ent_parent, prob_parent, hist_parent = get_ent_prob(parent_ind, w_d2_cache, neighbor_w)

        CDE_score_norm = compute_CDE(prob_child, prob_parent)
        CDE_score = compute_CDE(hist_child, hist_parent)
        CDE_score_inv = compute_CDE(hist_parent, hist_child)

        loss_raw_1 = order_loss_raw(hist_parent, hist_child, over_penalty_2)
        loss_raw_inv_1 = order_loss_raw(hist_child, hist_parent, over_penalty_2)
        loss_raw_2 = order_loss_raw(hist_parent, hist_child, over_penalty_1)

        if(child in word2vec_model.wv and parent in word2vec_model.wv):
            word2vec_sim = word2vec_model.wv.similarity(child, parent)
        else:
            word2vec_sim = 0

        loss_1, sol_a_1 = solve_LP_by_sort(prob_child, prob_parent, over_penalty_2)
        loss_inv, sol_a_inv = solve_LP_by_sort(prob_parent, prob_child, over_penalty_2)
        loss_2, sol_a_2 = solve_LP_by_sort(prob_child, prob_parent, over_penalty_1)
        loss_inv_2, sol_a_inv_2 = solve_LP_by_sort(prob_parent, prob_child, over_penalty_1)

        if is_hyper_rel(rel):

            if(CDE_score_inv<CDE_score):
                spec_correct['CDE_diff'].append(1)
            elif CDE_score_inv>CDE_score:
                spec_correct['CDE_diff'].append(0)

            if (ent_child < ent_parent):
                spec_correct['entropy_diff'].append(1)
            elif (ent_child > ent_parent):
                spec_correct['entropy_diff'].append(0)

            if (loss_1 < loss_inv):
                spec_correct['order_diff'].append(1)
            elif (loss_1 > loss_inv):
                spec_correct['order_diff'].append(0)

            if (loss_2 < loss_inv_2):
                spec_correct['order_diff_s_w'].append(1)
            elif (loss_2 > loss_inv_2):
                spec_correct['order_diff_s_w'].append(0)

            if (loss_raw_1 < loss_raw_inv_1):
                spec_correct['order_raw_diff'].append(1)
            elif (loss_raw_1 > loss_raw_inv_1):
                spec_correct['order_raw_diff'].append(0)

            if (SLQS_sub>0):
                spec_correct['SLQS_sub'].append(1)
            elif(SLQS_sub<0):
                spec_correct['SLQS_sub'].append(0)

        rnd_baseline = random.random()
        result_list.append([child, parent, data_i[2:], -(1 - CDE_score_inv) * CDE_score, -CDE_score, -CDE_score_norm,
                            (1.01 - loss_1) * (ent_child - ent_parent), loss_1 - loss_inv, loss_1, loss_2 - loss_inv_2,
                            loss_2, ent_child - ent_parent, loss_raw_1, loss_raw_2, -word2vec_sim,
                            word2vec_sim * (ent_child - ent_parent), loss_1 * (1.1 - loss_inv), rnd_baseline,
                            CDE_score_inv - CDE_score, -SLQS_sub, word2vec_sim * (ent_child - ent_parent)*(1.1 - loss_1)])

    print "total eval count", len(result_list)
    print "total oov count", len(oov_list)
    print oov_list[: min(len(oov_list), 10)]

    return result_list, spec_correct, method_ind_map

def compute_AP(result_list_method,is_hyper_rel):
    prec_list = []
    correct_count = 0
    all_count = 0
    rel_d2_count = {}
    rel_d2_prec_list = {}
    for i in range(len(result_list_method)):
        all_count += 1
        rel=result_list_method[i][2][1]
        if is_hyper_rel(rel):
            correct_count += 1
            prec_list.append(correct_count / float(all_count))
        else:
            if rel not in rel_d2_count:
                rel_d2_count[rel] = 0
                rel_d2_prec_list[rel] = []
            rel_d2_count[rel] += 1
            rel_d2_prec_list[rel].append(correct_count / float(correct_count+rel_d2_count[rel]))
    return np.mean(prec_list), rel_d2_prec_list, rel_d2_count


def output_AP(result_list_method, is_hyper_rel, method, rel_list):
    AP, rel_d2_prec_list, rel_d2_count = compute_AP(result_list_method, is_hyper_rel)
    print method, ": overall, ", "%.1f"%(AP*100), ", ", np.sum(rel_d2_count.values()), "; ",
    for rel in rel_list:
        if rel in rel_d2_prec_list:
            print rel, ", ", "%.1f"%(np.mean(rel_d2_prec_list[rel])*100), ", ", str(rel_d2_count[rel]), "; ",
    print