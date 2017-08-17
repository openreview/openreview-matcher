from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from openreview_matcher.keyphrase_extractor import base_extractor
from operator import itemgetter
import pickle

class KeyphraseExtractor(base_extractor.KeyphraseExtractor):
	""" 
	Tf-idf based keyphrase extractor 
	Assumes the inputs (document, corpus) are already preprocessed
	"""

	def __init__(self, params=None):

		with open("trained_models/tfidf/tfidfvectorizer.pkl", "r") as f:
			self.tfidf = pickle.load(f)

	def extract(self, document, top_n=5, corpus=None):
		"""
		Extract the 'best' keywords from a document using tf-idf
		"""

		keywords = self.get_top_words(document, top_n)
		return keywords

	def get_top_words(self, document, n):
		""" Get the top n words based on tf-idf scores from the document """

		output = list(self.tfidf.transform([document]).toarray()[0])
		features = self.tfidf.get_feature_names()
		tfidf_words = [(word, score) for word, score in zip(features, output) if score > 0.0]
		sorted_tfidf_words = sorted(tfidf_words, key=itemgetter(1), reverse=True)[:n]
		return [word[0] for word in sorted_tfidf_words]

	def __repr__(self):
		return "tfidf"
