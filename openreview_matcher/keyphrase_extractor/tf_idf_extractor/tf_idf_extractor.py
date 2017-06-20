from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from openreview_matcher.keyphrase_extractor import base_extractor
from operator import itemgetter


class KeyphraseExtractor(base_extractor.KeyphraseExtractor):
	""" 
	Tf-idf based keyphrase extractor 
	Assumes the inputs (document, corpus) are already preprocessed
	"""

	def __init__(self, params=None):
		pass

	def extract(self, document, top_n=5, corpus=None):
		"""
		Extract the 'best' keywords from a document using tf-idf
		"""

		top_n_words = self.__tf_idf(document, corpus)[:top_n]
	   	return [word[0] for word in top_n_words]

	def train_tf_idf_on_corpus(self, corpus):
		""" Train and fit the TfidfVectorizor on the corpus """

		self.tfidf = TfidfVectorizer()
		self.tfidf.fit(corpus)

	def __tf_idf(self, document, top_n=5):
	    """
	    Perform TF-IDF on the corpus and get back tfidf scores on the document

	    Arguments:
	        document: the document to apply tf-idf to. The document is a list of tokens
	        corpus: the collection of all documents representing the corpus. The corpus is represented
	        as a list of documents which are represented as a list of tokens

	        corpus = [["the", "model", "is", "really", "good"], ["i", "like", "building", "expertise", "models"]]
	    Returns:
	        a dictionary of terms with the tf-idf weights {term => tf-idf weight}
	    """
	    output = list(self.tfidf.transform([" ".join(document)]).toarray()[0])
	    features = self.tfidf.get_feature_names()
	    tfidf_words = [(word, score) for word, score in zip(features, output) if score > 0.0]
	    sorted_tfidf_words = sorted(tfidf_words, key=itemgetter(1), reverse=True) 
	    return sorted_tfidf_words