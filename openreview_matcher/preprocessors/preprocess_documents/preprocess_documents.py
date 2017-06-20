""" 
This script includes generate implementation of preprocessing utitlies 
such as stopword removal, lemmatization, normalization of abbreviations,etc...
"""

from nltk.corpus import stopwords
from gensim.models import Phrases

bigram_phrases = Phrases.load("data/bigram_phrases.pkl")
trigram_pharses = Phrases.load("data/trigram_phrases.pkl")

def stop_word_removal(doc_tokens):
    """ Apply stopword removal to the document """
    stop_words = set(stopwords.words("english"))
    return [word for word in doc_tokens if word not in stop_words]

def bigram_transformer(doc):
    """ Apply bigram phrase model on the document """
    return bigram_phrases[doc]

def trigram_transformer(doc):
    """ Apply a trigram phrase model on the document """
    return trigram_pharses[bigram_phrases[doc]]



