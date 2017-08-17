from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from openreview_matcher.keyphrase_extractor import base_extractor
from operator import itemgetter
import pickle

class KeyphraseExtractor(base_extractor.KeyphraseExtractor):
	""" 
	Assumes the inputs (document, corpus) are already preprocessed
	"""

	def __init__(self, params=None):
		pass

	def extract(self, document, top_n=5, corpus=None):
		"""
		Extract the 'best' keywords from a document using tf-idf
		"""

		return document.split()	

	def __repr__(self):
		return "no_keyword_extractor"
