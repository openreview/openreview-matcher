import sys, os
import imp
import csv
import argparse
import json
import numpy as np
import itertools
import time
import matplotlib 
import matplotlib.pyplot as plt
import pickle

from openreview_matcher import utils

matplotlib.style.use('ggplot')

"""

required arguments:
    --conf (-cf): 
        The conference (uai2017, iccv15) to run models on

    --models (-m):
        A list of model names to train or evaluate. Model names should exactly
        match the name of its corresponding directory in /models. Multiple
        names may be entered.

    --data_type (-dt)
        The type of data to evaluate models on. This could either be abstracts, title or titles_abstracts.
        In the future maybe in full_text

    --combine (-combine):
        The type of mechanism to use combine scores of all reviewers' documents
        Some options would be avg, max, logsumexp

        e.g. python --models bow_dirichlet_smooth --combine max

    --scoring (-scoring):
        The type of scoring mechanism to use to score against two documents. 
        Scoring options would include language model (lm), cosine_similarity, word_movers.

        e.g. python --models bow_dirichlet_smooth --combine max --scoring lm

    --fit (-f):
        Can either be True or False. This says if you want to fit the model on the training data (reviewer papers)

    --predict (-p):
        Can either be True or False. This says if you want to predict on the query papers using the trained model.
        Note: fit must be called on the model inorder to predict

    --keyphrase_extractor (-ke):
        The type of keyphrase extractor to apply to the models (eg. tf_idf_extractor)
        If you don't wish to run a keyphrase extractor then pass in "None"

        e.g. python --models bow_dirichlet_smooth --combine max --scoring lm --keyphrase_extractor tf_idf_extractor

    --eval_data (-ed):
        The location of the evaluation data (bids). The file should be a .pkl file

    --evals (-e)
        The type of evaluation to run on the evaluation data. This can be precision_at_m, recall_at_m,
        mean_avg_precision.

    --plot (-plt):
        Type of plot to make, such as recall/precision vs m, precision vs recall
    
    --save (-s):
        If provided, and if training data is provided, calls the model's
        serialize() method, writing a .pkl file to models/<model_name>.pkl

        e.g. python --models randomize --fit data/train.json --save
    
Example:

    python  main.py
            --models embedding
            --data_type abstracts
            --combine max
            --scoring cosine_similarity 
            --fit True
            --predict True 
            --keyphrase_extractor tf_idf_extractor
            --eval_data bids 
            --plot recall_vs_m
            --save

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


def save_model(model, conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor):
    serialize_dir = './saved_models/{0}'.format(conference_name)
    if not os.path.isdir(serialize_dir): os.makedirs(serialize_dir)
    serialize_path = serialize_dir+'/%s-%s-%s-%s-%s.pkl' % (model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor)
    print "    serializing model at %s." % serialize_path
    model.serialize(serialize_path)


def load_model(conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor):
    try:
        print "    loading %s model from saved_models/%s/%s-%s-%s-%s-%s.pkl" % (model_name, conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor)
        model = utils.load_obj('./saved_models/%s/%s-%s-%s-%s-%s.pkl' % (conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor))
        return model
    except IOError as e:
        print "    [ERROR] unable to find serialized model \"%s\"." % model_name
        return None


def train_model(model, model_name, train_data_path, archive_data_path):
    train_data = utils.SerializedData(os.path.join(os.path.dirname(__file__), train_data_path))
    archive_data = utils.SerializedData(os.path.join(os.path.dirname(__file__), archive_data_path))

    print "    fitting %s model..." % model_name
    model.fit(train_data=train_data, archive_data=archive_data)

    print "    %s model training done." % model_name

    return model


def test_model(model, model_name, test_data_path):

    print("Testing model: {0}".format(model_name))
    test_data = utils.SerializedData(os.path.join(os.path.dirname(__file__), test_data_path))
    ranklists = []

    print "    predicting with %s model..." % model_name

    ranks_path = ranks_directory + '/%s-ranks.csv' % model_name 
    rank_dir = os.path.dirname(ranks_path)
 
    if not os.path.exists(rank_dir):
        os.makedirs(rank_dir)

    # if not os.path.isdir(ranks_path): os.makedirs(ranks_path)

    # ranks_path = ranks_path + "%s-ranks.csv" % (model_name)
    f = open(ranks_path, 'w')
    ranks_writer = csv.writer(f)

    for idx, note_record in enumerate(test_data, start=1):  
        if idx % 5 == 0:
            print("Predicting on submission paper {0}".format(idx))
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
    ranks_path = ranks_directory + '/%s-ranks.csv' % (model_name)

    try:
        f = open(ranks_path)
        ranks_by_forum = [(row[0],row[1:]) for row in csv.reader(f)]
        f.close()
    except IOError:
        return None

    return ranks_by_forum


def evaluate_model(evaluator, model_name, ranklists):
    eval_path = evals_directory + '/%s-eval.csv' % model_name
    eval_directory = os.path.dirname(eval_path)
 
    if not os.path.exists(eval_directory):
        os.makedirs(eval_directory)

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

    # for eval_scores in evaluator.evaluate(ranklists):
    #     print(eval_scores)
    #     eval_writer.writerow([str(val) for val in eval_scores])
    #     all_scores.append(eval_scores[1])

    for forum, scores in evaluator.evaluate(ranklists):
        eval_writer.writerow([forum]+scores)
        all_scores.append(scores)

    if all_scores:
        avg_scores = np.mean(all_scores, axis=0)
    else:
        avg_scores = []

    s = open('results/summary.csv','a')
    sample_writer = csv.writer(s)
    sample_writer.writerow([eval_name, model_name] + list(all_scores))
    s.close()
 
    g.close()

    return avg_scores

def graph_model_ranks(model_name, ranklists, graph_type, ax, eval_data):

    graph_source = imp.load_source(graph_type, './openreview_matcher/graphing/%s/%s.py' % (graph_type, graph_type))
    grapher = graph_source.Graphing(eval_data=eval_data)
    ax = grapher.graph(ranklists, ax, model_name)
    return ax

def TrainedModels(conference_name, data_types, model_names, combining_mechanisms, scoring_mechanisms, keyphrase_extractor, fit_model, save):
    """
    TrainedModels() returns a generator object which yields a trained model object and
    its name.
    """

    model_permutations = list(itertools.product(*[args.models, args.combine, args.scoring, data_types, [repr(keyphrase_extractor)]]))

    for model_number, model_permutation in enumerate(model_permutations):
        model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor = model_permutation

        print "({0} or {1}) {2} using {3} and {4}".format(model_number+1,len(model_permutations), model_name, combining_mechanism, scoring_mechanism)
        print "Input Data: {0}".format(data_type)
        print "Extacting Keywords using: {0}".format(keyword_extractor)
        print "\n"

        model_source = imp.load_source(model_name, './openreview_matcher/models/%s/%s.py' % (model_name, model_name))

        if fit_model:
            train_data_path = "./data/conference/{0}/{0}_train.json".format(conference_name)
            archive_data_path = "./data/conference/{0}/{0}_archive_{1}.json".format(conference_name, data_type) 
            
            model_params = get_model_params(model_name)
            model = model_source.Model(params=model_params, combinining_mechanism=combining_mechanism, scoring_mechanism=scoring_mechanism, keyphrase_extractor=keyphrase_extractor)
            model = train_model(model, model_name, train_data_path, archive_data_path)
            if save: save_model(model, conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor)

        else:
            if save: print "[WARNING] Cannot save: training data not provided. Loading model instead."
            # if not train_data_path: print "    train data not provided."
            # if not archive_data_path: print "    archive data not provided."
            model = load_model(conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor)
        if model:
            yield model, "{0}/{1}-{2}-{3}-{4}-{5}".format(conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor)
        else:
            pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument('-cf', '--conf', help="list of conferences to evaluate model on", required=True) 
    parser.add_argument('-dt', '--data_type', nargs="+", help="type of input data (titles, abstract, fulltext", required=True)
    parser.add_argument('-m','--models', nargs='+', help="list of model names to train or evaluate", required=True)
    parser.add_argument('-c', '--combine', nargs="+", help="type of mechanism to combine reviewer document scores", required=True)
    parser.add_argument('-sc', '--scoring', nargs="+", help="type of scoring mechanism to score documents", required=True)
    parser.add_argument('-ke', '--keyphrase_extractor', help="type of keyphrase extraction to use")
    parser.add_argument('-f','--fit', help="whether or not to fit the models on the training data")
    parser.add_argument('-p','--predict', help="whether or not to predict on the test data")
    parser.add_argument('-e','--evals', nargs='+', help="list of evaluator names")
    parser.add_argument('-ed', '--eval_data', help="location of evaluation data (bids) ")
    parser.add_argument('-s','--save', action='store_true', help="if included, serializes the model.")
    parser.add_argument('-plt', '--plot', nargs="+", help="plot the output of the ranks of the models") # NOTE: add to the documentation later

    args = parser.parse_args()
    conference_name = args.conf 

    # test_data_path = args.predict
    eval_names = args.evals if args.evals else []
    
    # get all of the model permutations (model, scoring mechanism, combining mechanism)
    saved_models = [file.split(".")[0] for file in os.listdir("./saved_models/{0}".format(conference_name))]
 
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

    model_permutations = list(itertools.product(*[args.models, args.combine, args.scoring, args.data_type, [repr(extractor)]]))
    model_permutations = [model_perm for model_perm in model_permutations if "-".join(list(model_perm)) in saved_models]

    print "Testing models on data from", conference_name, "conference"

    conf_predict_data = "./data/conference/{0}/{0}_test.json".format(conference_name)

    ranklists_by_model = {}
    for model, model_name in TrainedModels(conference_name, args.data_type, args.models, args.combine, args.scoring, 
                                            extractor, args.fit, args.save):
        if args.predict:
            ranklists = test_model(model, model_name, conf_predict_data)
            ranklists_by_model[model_name] = ranklists
        else:
            ranklists_by_model[model_name] = load_ranklists(model_name)

    # you can only evaluate your models if you pass in evaluation data
    if args.evals and args.eval_data:

        print "Loading evaluation data (bids)..."
        with open(args.eval_data, "r") as f:
            eval_data_bids = pickle.load(f) # load in the evaluation data (bids)

        for eval_number, eval_name in enumerate(eval_names):

            eval_source = imp.load_source(eval_name, './openreview_matcher/evals/%s/%s.py' % (eval_name, eval_name))
            evaluator = eval_source.Evaluator(eval_data=eval_data_bids, params=get_eval_params(eval_name))
            
            if ranklists_by_model: print "evaluating %s (evaluation %s of %s):" % (eval_name, eval_number+1, len(eval_names))

            for model_number, model_permutation in enumerate(model_permutations):
                model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor = model_permutation
                model_name = "{0}/{1}-{2}-{3}-{4}-{5}".format(conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor)
                ranklists = ranklists_by_model[model_name]
                avg_scores = evaluate_model(evaluator, model_name, ranklists)

                if len(avg_scores)>0: print "    %-20s (model %s of %s): %s" % (model_name, model_number+1, len(args.models), avg_scores)

    # you can only plot if you pass in eval_data
    if args.plot and args.eval_data:

        with open(args.eval_data, "r") as f:
            eval_data_bids = pickle.load(f) # load in the evaluation data (bids)

        for plt_type in args.plot:
            # for each type of plot
            fig, ax = plt.subplots()
            for model_number, model_permutation in enumerate(model_permutations):
                model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor = model_permutation
                model_name = "{0}/{1}-{2}-{3}-{4}-{5}".format(conference_name, model_name, combining_mechanism, scoring_mechanism, data_type, keyword_extractor) 
                ranklists = ranklists_by_model[model_name]
                print("Computing {0} for {1}".format(plt_type, model_name))
                ax = graph_model_ranks(model_name, ranklists, plt_type, ax, eval_data_bids)
            plt.tight_layout()
            plt.show()

            fig_dir = "results/figures/{0}".format(conference_name) 
            if not os.path.exists(fig_dir):
                os.makedirs(fig_dir) 

            fig.savefig("results/figures/{0}/{1}.png".format(conference_name, plt_type), dpi=200)

