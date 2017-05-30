from __future__ import division
import csv
import json
from collections import defaultdict
from operator import itemgetter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import random
import string
from gensim.models import LdaModel
from gensim import corpora
from models import base_model
from util.preprocess import *

class Model(base_model.Model):
	""" Implementation of LDA based expertise model """

	def __init__(self, params=None):
		self.num_topics = params["num_topics"]

	def fit(self, train_data, archive_data):
		"""
		Fits the LDA topic model on the reviewer archive and the test papers

		Arguments
			@train_data: a list of records containing training documents
			@reviewer_archive: an iterator over records that contains the reviewer's archive

		Returns
			None
		"""

		corpus = []

		for paper in train_data:
			if(paper['content']['archive']):
				corpus.append(clean_text(paper['content']['archive']))

		for record in archive_data:
			if(record["content"]["archive"]):
				corpus.append(clean_text(record["content"]["archive"]))

		reviewer_to_papers = defaultdict(list)

		for record in archive_data:
			if(record["content"]["archive"]):
				reviewer_to_papers[record["reviewer_id"]].append(clean_text(record["content"]["archive"]))

		self.reviewers = reviewer_to_papers.keys()

		corpus = [[word for word in document.lower().split()]
				for document in corpus]

		self.dictionary = corpora.Dictionary(corpus)
		self.corpus_bow = [self.dictionary.doc2bow(doc) for doc in corpus]

		print("Training LDA Model")
		self.lda = LdaModel(corpus=self.corpus_bow, id2word=self.dictionary, num_topics=self.num_topics, update_every=1, chunksize=830, passes=20)
		self.reviewer_to_lda_vector = self.___build_reviewer_lda_vector(dict(reviewer_to_papers))

		return self


	def predict(self, test_record):
		forum_id = test_record["forum"]
		paper = clean_text(test_record["content"]["archive"])
		paper_to_reviewer_scores = []
		paper_lda_vector = self.__build_lda_topic_vector(paper)


		for reviewer in self.reviewers:
			reviewer_lda_vector = self.reviewer_to_lda_vector[reviewer]
			score = cosine_similarity(paper_lda_vector.reshape(1, -1), reviewer_lda_vector.reshape(1, -1))
			paper_to_reviewer_scores.append((reviewer, score))

		ranked_reviewer_list = [reviewer_scores[0] for reviewer_scores in sorted(paper_to_reviewer_scores, key=itemgetter(1))]
		return ranked_reviewer_list

	def __build_lda_topic_vector(self, document):
		num_topics = range(1, self.num_topics)
		topic_vec = []
		lda_raw_topic_distribution = dict(self.lda[self.dictionary.doc2bow(document.split())])
		for topic_num in num_topics:
			if topic_num not in lda_raw_topic_distribution:
				topic_vec.append(0.0)
			else:
				topic_vec.append(lda_raw_topic_distribution[topic_num])
		return np.asarray(topic_vec)

	def ___build_reviewer_lda_vector(self, reviewers):
		""" Builds a dictionary of all reviewer lda vectors """

		reviewer_to_lda_vector = {}
		for reviewer, papers in reviewers.iteritems():
			print("\n")
			reviewer_matrix = np.vstack(map(lambda doc: self.__build_lda_topic_vector(doc), papers))
			reviewer_to_lda_vector[reviewer] = np.mean(reviewer_matrix, axis=0)
		return reviewer_to_lda_vector
