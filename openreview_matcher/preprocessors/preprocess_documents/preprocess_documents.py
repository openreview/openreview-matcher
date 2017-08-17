# -*- coding: utf-8 -*-

""" 
This script includes general implementation of preprocessing utitlies 
such as stopword removal, lemmatization, normalization of abbreviations, 
normalizing ascii characters etc...
"""

from nltk.corpus import stopwords
from gensim.models import Phrases
import re 
import unicodedata

bigram_model = Phrases.load("trained_models/phrase/bigram_model.bin")
trigram_model = Phrases.load("trained_models/phrase/trigram_model.bin")

def trigram_transformer(words):
    """ Transform a document into a document with phrases using the learned phrase model """

    # words = tokenize(doc)
    bigrams = bigram_model[words]
    trigrams = trigram_model[bigrams]
    return trigrams

def stop_word_removal(doc_tokens):
    """ Apply stopword removal to the document """
    stop_words = set(stopwords.words("english"))
    return [word for word in doc_tokens if word not in stop_words]

def tokenize(line):
    """ 
    Tokenize the document into words or tokens 
    
    Returns a python list of tokens
    """

    # üñèéóãàáíøö¨úïäýâåìçôêßëîÁÅÇÉÑÖØÜ]')
   
    line = line.replace('-\n', "")
    line = line.replace("- ", "_")
    line = line.replace("-", "_") 
    line = line.replace("_ ", " ")
    line = line.replace(" _", " ")
    line = line.replace("_", " ")

    line = line.lower()
    space_regexp = re.compile('[^a-zA-Z_]')
    line = sanitize(line)  # sanitize returns unicode
    words = re.split(space_regexp, line)
    words = filter(lambda x: len(x) > 2, words)
    words = stop_word_removal(words)

    return words

def sanitize(w):
    """
    sanitize (remove accents and standardizes)
    """

    # print w

    map = {'æ': 'ae',
        'ø': 'o',
        '¨': 'o',
        'ß': 'ss',
        'Ø': 'o',
        '\xef\xac\x80': 'ff',
        '\xef\xac\x81': 'fi',
        '\xef\xac\x82': 'fl'}

    # This replaces funny chars in map
    for char, replace_char in map.iteritems():
        w = re.sub(char, replace_char, w)

    # w = unicode(w, encoding='utf-8')

    # This gets rite of accents
    w = ''.join((c for c in unicodedata.normalize(
        'NFD', w) if unicodedata.category(c) != 'Mn'))

    return w



