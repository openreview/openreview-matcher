import sys, os
import imp
import csv
import argparse
import json
import numpy as np

from openreview_matcher import utils

"""

required arguments:
    --models (-m):
        A list of model names to train or evaluate. Model names should exactly
        match the name of its corresponding directory in /models. Multiple
        names may be entered.

        e.g. python --models randomize tfidf

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

    --save (-s):
        If provided, and if training data is provided, calls the model's
        serialize() method, writing a .pkl file to models/<model_name>.pkl

        e.g. python --models randomize --fit data/train.json --save


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


def save_model(model, model_name):
    serialize_dir = './saved_models'
    if not os.path.isdir(serialize_dir): os.makedirs(serialize_dir)
    serialize_path = serialize_dir+'/%s.pkl' % model_name
    print "    serializing model at %s." % serialize_path
    model.serialize(serialize_path)

def load_model(model_name):
    try:
        print "    loading %s model from saved_models/%s.pkl" % (model_name, model_name)
        model = utils.load_obj('./saved_models/%s.pkl' % model_name)
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
    for note_record in test_data:
        forum = note_record['forum']
        rank_list = model.predict(note_record)
        ranks = [r.encode('utf-8') for r in rank_list]
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

    for forum, scores in evaluator.evaluate(ranklists):
        eval_writer.writerow([forum]+scores)
        all_scores.append(scores)

    if all_scores:
        avg_scores = np.mean(all_scores, axis=0)
    else:
        avg_scores = []

    s = open('results/summary.csv','a')
    sample_writer = csv.writer(s)
    sample_writer.writerow([eval_name, model_name] + list(avg_scores))
    s.close()

    g.close()

    return avg_scores

def TrainedModels(model_names, train_data_path, archive_data_path, save):
    """
    TrainedModels() returns a generator object which yields a trained model object and
    its name.

    """
    for model_number, model_name in enumerate(model_names):

        print "%s (model %s of %s):" % (model_name, model_number+1, len(model_names))
        model_source = imp.load_source(model_name, './openreview_matcher/models/%s/%s.py' % (model_name, model_name))

        if train_data_path and archive_data_path:
            model = model_source.Model(params=get_model_params(model_name))
            model = train_model(model, model_name, train_data_path, archive_data_path)
            if save: save_model(model, model_name)

        else:
            if save: print "[WARNING] Cannot save: training data not provided. Loading model instead."
            if not train_data_path: print "    train data not provided."
            if not archive_data_path: print "    archive data not provided."
            model = load_model(model_name)

        if model:
            yield model, model_name
        else:
            pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument('-m','--models', nargs='+', help="list of model names to train or evaluate", required=True)
    parser.add_argument('-f','--fit', help="a path to a .json file containing the training records")
    parser.add_argument('-a','--archive', help="a path to the .json file containing the reviewer archives")
    parser.add_argument('-p','--predict', help="a path to a .json file containing the test records")
    parser.add_argument('-e','--evals', nargs='+', help="list of evaluator names")
    parser.add_argument('-s','--save', action='store_true', help="if included, serializes the model.")

    args = parser.parse_args()

    test_data_path = args.predict
    eval_names = args.evals if args.evals else []

    ranks_directory = 'results/ranks'
    if not os.path.isdir(ranks_directory): os.makedirs(ranks_directory)

    evals_directory = 'results/evals'
    if not os.path.isdir(evals_directory): os.makedirs(evals_directory)

    ranklists_by_model = {}
    for model, model_name in TrainedModels(args.models, args.fit, args.archive, args.save):
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
            for model_number, model_name in enumerate(args.models):
                ranklists = ranklists_by_model[model_name]
                avg_scores = evaluate_model(evaluator, model_name, ranklists)

                if len(avg_scores)>0: print "    %-20s (model %s of %s): %s" % (model_name, model_number+1, len(args.models), avg_scores)



