import sys, os
import imp
import csv
import argparse
import json
import numpy as np
import itertools
import time
from openreview_matcher import utils

import matplotlib 
import matplotlib.pyplot as plt
matplotlib.style.use('ggplot')

# from openreview_matcher.graphing.precision_recall_curve import precision_recall_curve
"""

required arguments:
    --models (-m):
        A list of model names to train or evaluate. Model names should exactly
        match the name of its corresponding directory in /models. Multiple
        names may be entered.

    --combine (-combine):
        The type of mechanism to use combine scores of all reviewers' documents
        Some options would be avg, max, logsumexp

        e.g. python --models bow_dirichlet_smooth --combine max

    --scoring (-scoring):
        The type of scoring mechanism to use to score against two documents. 
        Scoring options would include language model (lm), cosine_similarity, word_movers.

        e.g. python --models bow_dirichlet_smooth --combine max --scoring lm
    
optional arguments:
    --fit (-f):
        The path to a .json file containing the training data. Each line should
        be a JSON record of a single training document. All records should have
        a "content" field and a "forum" field.

        e.g. python --models randomize --fit data/train.json

    --archive (-a):
        The path to a .json file containing the reviewer archive data. Each line
        should be a JSON record of a single training document. All records should
        have a "content" field and a "forum" field.

        e.g. python --models randomize --fit data/archive.json

    --predict (-p):
        The path to a .json file containing the test data. Each line should
        be a JSON record of a single training document. All records should
        have a "content" field and a "forum" field.

        e.g. python --models randomize --predict data/test.json

    --evals (-e):
        A list of evaluation methods to use on the models. Evaluation names
        should exactly match the name of its corresponding directory in
        /models. Multiple names may be entered.

        e.g. python --models randomize tfidf --evals recall_at_m

    --plot (-plt):
        Type of plot to make, such as recall/precision vs m, precision vs recall
    
    --save (-s):
        If provided, and if training data is provided, calls the model's
        serialize() method, writing a .pkl file to models/<model_name>.pkl

        e.g. python --models randomize --fit data/train.json --save
    
Example:

    python --models bow_dirichlet_smooth --combine max --scoring cosine_similarity --fit data/train.json 
            --archive data/arhive.json --predict data/test.json --evals recall_at_m --save

"""

def get_model_params(model_name):
    params_path = 'openreview_matcher/models/%s/%s-params.json' % (model_name, model_name)
    try:
        f = open(params_path)
        params = json.load(f)
        f.close()
        print "    model params loaded from %s" % params_path
        return params
    except IOError:
        print "    no model params found at %s" % params_path
        return None


def get_eval_params(eval_name):
    params_path = 'openreview_matcher/evals/%s/%s-params.json' % (eval_name, eval_name)
    try:
        f = open(params_path)
        params = json.load(f)
        f.close()
        print "    eval params loaded from %s" % params_path
        return params
    except IOError:
        print "    no eval params found at %s" % params_path
        return None


def save_model(model, model_name, combining_mechanism, scoring_mechanism):
    serialize_dir = './saved_models'
    if not os.path.isdir(serialize_dir): os.makedirs(serialize_dir)
    serialize_path = serialize_dir+'/%s-%s-%s.pkl' % (model_name, combining_mechanism, scoring_mechanism)
    print "    serializing model at %s." % serialize_path
    model.serialize(serialize_path)


def load_model(model_name, combining_mechanism, scoring_mechanism):
    try:
        print "    loading %s model from saved_models/%s-%s-%s.pkl" % (model_name, model_name, combining_mechanism, scoring_mechanism)
        model = utils.load_obj('./saved_models/%s-%s-%s.pkl' % (model_name, combining_mechanism, scoring_mechanism))
        return model
    except IOError as e:
        print "    [ERROR] unable to find serialized model \"%s\". To train and save the model, run: " % model_name
        print "    python main.py --models %s --fit <training_data> --archive <archive_data> --save" % model_name
        return None


def train_model(model, model_name, train_data_path, archive_data_path):
    train_data = utils.SerializedData(os.path.join(os.path.dirname(__file__), train_data_path))
    archive_data = utils.SerializedData(os.path.join(os.path.dirname(__file__), archive_data_path))

    print "    fitting %s model..." % model_name
    model.fit(train_data=train_data, archive_data=archive_data)

    print "    %s model training done." % model_name

    return model


def test_model(model, model_name, test_data_path):
    test_data = utils.SerializedData(os.path.join(os.path.dirname(__file__), test_data_path))
    ranklists = []

    print "    predicting with %s model..." % model_name
    ranks_path = ranks_directory + '/%s-ranks.csv' % model_name

    f = open(ranks_path, 'w')
    ranks_writer = csv.writer(f)
    for note_record in test_data:  # skip every five
        forum = note_record['forum']
        rank_list = model.predict(note_record)
        ranks = [r for r in rank_list]
        ranks_writer.writerow([forum]+ranks)
        ranklists.append((forum, ranks))
    f.close()
    print "    writing to " + ranks_path
    print "    %s testing done." % model_name

    return ranklists


def load_ranklists(model_name):
    ranks_path = ranks_directory + '/%s-ranks.csv' % model_name

    try:
        f = open(ranks_path)
        ranks_by_forum = [(row[0],row[1:]) for row in csv.reader(f)]
        f.close()
    except IOError:
        return None
    return ranks_by_forum


def evaluate_model(evaluator, model_name, ranklists):
    eval_path = evals_directory + '/%s-eval.csv' % model_name

    all_scores = []

    if not ranklists:
        try:
            ranks_path = ranks_directory + '/%s-ranks.csv' % model_name
            f = open(ranks_path)
            ranks_reader = csv.reader(f)
            ranklists = [(row[0], row[1:]) for row in ranks_reader]
            f.close()
        except IOError:
            print "    [ERROR] unable to find rank list for model \"%s\". To generate rank lists for the model, run: " % model_name
            print "    python main.py --models %s --predict <test_data>" % model_name
            return []

    g = open(eval_path, 'w')
    eval_writer = csv.writer(g)

    for eval_scores in evaluator.evaluate(ranklists):
        eval_writer.writerow([str(val) for val in eval_scores])
        all_scores.append(eval_scores[1])
    # for forum, scores in evaluator.evaluate(ranklists):
    #     eval_writer.writerow([forum]+scores)
    #     all_scores.append(scores)

    # if all_scores:
    #     avg_scores = np.mean(all_scores, axis=0)
    # else:
    #     avg_scores = []

    s = open('results/summary.csv','a')
    sample_writer = csv.writer(s)
    sample_writer.writerow([eval_name, model_name] + list(all_scores))
    s.close()
 
    g.close()

    return all_scores

def graph_model_ranks(model_name, ranklists, graph_type, ax):
    graph_source = imp.load_source(graph_type, './openreview_matcher/graphing/%s/%s.py' % (graph_type, graph_type))
    grapher = graph_source.Graphing()
    ax = grapher.graph(ranklists, ax, model_name)
    return ax

def TrainedModels(model_names, combining_mechanisms, scoring_mechanisms, keyphrase_extractor, train_data_path, archive_data_path, save):
    """
    TrainedModels() returns a generator object which yields a trained model object and
    its name.

    """

    model_permutations = list(itertools.product(*[args.models, args.combine, args.scoring]))

    for model_number, model_permutation in enumerate(model_permutations):
        model_name, combining_mechanism, scoring_mechanism = model_permutation
        print "({0} or {1}) {2} using {3} and {4}".format(model_number+1,len(model_permutations), model_name, combining_mechanism, scoring_mechanism)
        model_source = imp.load_source(model_name, './openreview_matcher/models/%s/%s.py' % (model_name, model_name))

        if train_data_path and archive_data_path:
            model_params = get_model_params(model_name)
            model = model_source.Model(params=model_params, combinining_mechanism=combining_mechanism, scoring_mechanism=scoring_mechanism, keyphrase_extractor=keyphrase_extractor)
            model = train_model(model, model_name, train_data_path, archive_data_path)
            if save: save_model(model, model_name, combining_mechanism, scoring_mechanism)

        else:
            if save: print "[WARNING] Cannot save: training data not provided. Loading model instead."
            if not train_data_path: print "    train data not provided."
            if not archive_data_path: print "    archive data not provided."
            model = load_model(model_name, combining_mechanism, scoring_mechanism)

        if model:
            yield model, "{0}-{1}-{2}".format(model_name, combining_mechanism, scoring_mechanism)
        else:
            pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument('-m','--models', nargs='+', help="list of model names to train or evaluate", required=True)
    parser.add_argument('-c', '--combine', nargs="+", help="type of mechanism to combine reviewer document scores", required=True)
    parser.add_argument('-sc', '--scoring', nargs="+", help="type of scoring mechanism to score documents", required=True)
    parser.add_argument('-ke', '--keyphrase_extractor', help="type of keyphrase extraction to use")
    parser.add_argument('-f','--fit', help="a path to a .json file containing the training records")
    parser.add_argument('-a','--archive', help="a path to the .json file containing the reviewer archives")
    parser.add_argument('-p','--predict', help="a path to a .json file containing the test records")
    parser.add_argument('-e','--evals', nargs='+', help="list of evaluator names")
    parser.add_argument('-s','--save', action='store_true', help="if included, serializes the model.")
    parser.add_argument('-plt', '--plot', nargs="+", help="plot the output of the ranks of the models") # NOTE: add to the documentation later

    args = parser.parse_args()
    test_data_path = args.predict
    eval_names = args.evals if args.evals else []

    saved_models = [file.split(".")[0] for file in os.listdir("./saved_models")]
    model_permutations = list(itertools.product(*[args.models, args.combine, args.scoring]))
    model_permutations = [model_perm for model_perm in model_permutations if "-".join(list(model_perm)) in saved_models]


    ranks_directory = 'results/ranks'
    if not os.path.isdir(ranks_directory): os.makedirs(ranks_directory)

    evals_directory = 'results/evals'
    if not os.path.isdir(evals_directory): os.makedirs(evals_directory)


    # get the keyphrase extractor
    if args.keyphrase_extractor:
        keyphrase_extractor = args.keyphrase_extractor
        extractor_source = imp.load_source(keyphrase_extractor, './openreview_matcher/keyphrase_extractor/%s/%s.py' % (keyphrase_extractor, keyphrase_extractor)) 
        extractor = extractor_source.KeyphraseExtractor()  
    else:
        extractor = None
        
    ranklists_by_model = {}
    for model, model_name in TrainedModels(args.models, args.combine, args.scoring, extractor, args.fit, args.archive, args.save):
        if args.predict:
            ranklists = test_model(model, model_name, args.predict)
            ranklists_by_model[model_name] = ranklists
        else:
            ranklists_by_model[model_name] = load_ranklists(model_name)

    if args.evals:
        for eval_number, eval_name in enumerate(eval_names):
            eval_source = imp.load_source(eval_name, './openreview_matcher/evals/%s/%s.py' % (eval_name, eval_name))
            evaluator = eval_source.Evaluator(params=get_eval_params(eval_name))

            if ranklists_by_model: print "evaluating %s (evaluation %s of %s):" % (eval_name, eval_number+1, len(eval_names))

            for model_number, model_permutation in enumerate(model_permutations):
                model_name, combining_mechanism, scoring_mechanism = model_permutation
                model_name = "{0}-{1}-{2}".format(model_name, combining_mechanism, scoring_mechanism)
                ranklists = ranklists_by_model[model_name]
                avg_scores = evaluate_model(evaluator, model_name, ranklists)

                if len(avg_scores)>0: print "    %-20s (model %s of %s): %s" % (model_name, model_number+1, len(args.models), avg_scores)

    if args.plot:

        for plt_type in args.plot:
            # for each type of plot
            fig, ax = plt.subplots()
            for model_number, model_permutation in enumerate(model_permutations):
                model_name, combining_mechanism, scoring_mechanism = model_permutation
                model_name = "{0}-{1}-{2}".format(model_name, combining_mechanism, scoring_mechanism) 
                ranklists = ranklists_by_model[model_name]
                print("Computing {0} for {1}".format(plt_type, model_name))
                ax = graph_model_ranks(model_name, ranklists, plt_type, ax)
            print("Saving fig: ", plt_type)
            plt.tight_layout()
            fig.savefig("results/figures/{0}.png".format(plt_type), dpi=200)

