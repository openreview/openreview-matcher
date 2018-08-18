from __future__ import print_function
import sys,os
import pickle
import json
import imp

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '*'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total:
        print()

def save_obj(obj, name):
    sanitized_name = name.replace('.pkl','')
    with open(sanitized_name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name):
    sanitized_name = name.replace('.pkl','')
    with open(sanitized_name + '.pkl', 'rb') as f:
        return pickle.load(f)

def load_model(model_name):
    model_source = imp.load_source(model_name, os.path.join(os.path.dirname(__file__), '../models/%s/%s.py' % (model_name, model_name)))
    model = load_obj(os.path.join(os.path.dirname(__file__), '../../saved_models/%s/%s.pkl' % (model_name, model_name)))
    return model

class SerializedData(object):
    def __init__(self, filepath):
        self.filepath = filepath

    def __iter__(self):
        with open(self.filepath) as f:
            for line in f:
                # assume there's one json record per line
                yield json.loads(line)

def openreview_to_record(openreview_note, reviewer=None):
    note = openreview_note.to_json()

    if reviewer: note['reviewer_id'] = reviewer.encode('utf-8')

    for field in ['readers','replyto','nonreaders','tcdate','original','referent','cdate','writers','invitation','id','ddate','forumContent','signatures']:
        note.pop(field)

    title = note['content']['title']
    try:
        abstract = note['content']['abstract']
        abstract = " " + abstract
    except KeyError:
        abstract = ""

    try:
        tldr = note['content']['TL;DR']
        tldr = " " + tldr
    except KeyError:
        tldr = ""

    content = title + tldr + abstract

    note['content']['archive'] = content


    return note
