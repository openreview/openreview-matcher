""" A document embedding model trained using doc2vec (paragraph vectors) """

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Doc2Vec 
from random import shuffle
from gensim import corpora
from collections import Counter, defaultdict
from operator import itemgetter
import sys
from openreview_matcher.preprocessors import preprocess_documents
from openreview_matcher import eval_utils
import pickle
from gensim.models.doc2vec import TaggedDocument
from openreview_matcher.models import base_model

class Model(base_model.Model):
	""" Doc2Vec expertise model """

	def __init__(self, combinining_mechanism, scoring_mechanism, keyphrase_extractor, params=None):
		self.combinining_mechanism = combinining_mechanism
        self.scoring_mechanism = scoring_mechanism
        self.keyphrase_extractor = keyphrase_extractor
	    self.reviewers = []
	    self.model = Doc2Vec.load(params["doc2vec_location"]) # need to load in a saved doc2vec model
	    self.reviewer_to_papers = defaultdict(list) # a dictionary of reviewer document vectors (reviewer_name ==> list of doc vectors)
	    self.all_papers_to_inferred_vectors = {} # a dictionary of all papers (reviewer archive + test query papers to their doc embeddings)

	def fit(self, train_data, archive_data):

		# build the reviewer_archive

		print "Inferring vectors on documents of the reviewer archive ..."

		for record in archive_data:
		    if record["content"]['archive']:
		        paper = record["content"]["archive"]

		       	# get the document embedding for this paper 
		        paper_doc_vec = self.infer_new_document(paper)
		        self.all_papers_to_inferred_vectors[paper] = paper_doc_vec

		        reviewer_to_papers[record["reviewer_id"]].append(paper)

		self.reviewers = reviewer_to_papers.keys()

		print "Inferring vectors on documents of the test papers ..."

		for record in train_data:
		    if record["content"]['abstract']:
		        paper = " ".join(preprocess_documents.trigram_transformer(self.__tokenize_paper(record["content"]["abstract"])))
		       	paper_doc_vec = self.infer_new_document(paper)
		       	self.all_papers_to_inferred_vectors[paper] = paper_doc_vec

    def predict(self, test_record):
        """
        Given a new test record (submission file), predict computes an
        expertise score between all reviewers and the new record
    
        Arguments:
            test_record: paper to score
        Returns:
            a ranked list of reviewers that best match this paper
        """

        paper_to_reviewer_scores = []

        for reviewer in self.reviewers:
            expertise_score = self.score(reviewer, test_record)
            paper_to_reviewer_scores.append((reviewer, expertise_score))

        sorted_reviewer_scores = sorted(paper_to_reviewer_scores, key=itemgetter(1), reverse=True)
        ranked_reviewer_list = ["{0};{1}".format(reviewer_scores[0].encode('utf-8'),reviewer_scores[1]) for
                                reviewer_scores in sorted_reviewer_scores]

        return ranked_reviewer_list 

    def score(self, signature, note_record):
        """
        Returns an expertise score between a reviewer and a paper 
        Computes the averaged word vector for the reviewer and the
        paper and then uses cosine similarity on both vectors to create
        an expertise score between a reviewer and a paper

        Arguments:
            signature: reviewer_id
            note_record: a dict representing a note (paper)
        Returns:
            A float representing the score
        """

        if self.combinining_mechanism == "max":
            # compute the max score
            return self.compute_max_score(signature, note_record)
            
        elif self.combinining_mechanism == "avg":
            # compute the avg score
            return self.compute_avg_score(signature, note_record)

    def compute_max_score(self, signature, note_record):
        """ Take the max score between the paper vector and the reviewer document vectors """

        # self.keyphrase_extractor.train_tf_idf_on_corpus(self.testing_corpus)

        paper = " ".join(preprocess_documents.trigram_transformer(self.__tokenize_paper(note_record["content"]["abstract"])))
       	
       	paper_vector = self.all_papers_to_inferred_vectors[paper]

        reviewer_paper_scores = []

        for reviewer_paper in self.reviewer_to_papers[signature]:
            if self.scoring_mechanism == "cosine_similarity":
                # compute the cosine similarity between reviewer vector and paper vector

                if reviewer_paper_vec.size > 1: # because the reviewer paper vector is empty (nan), the words in the paper don't have word vectors

                	# get the document embedding for the reviewer paper word
                	reviewer_paper_vec = self.all_papers_to_inferred_vectors[paper]

                    reviewer_paper_score = self.compute_cosine_between_reviewer_paper(reviewer_paper_vec, paper_vector)
                    reviewer_paper_scores.append(reviewer_paper_score)

            elif self.scoring_mechanism == "wmd":
                # compute the word movers distance between reviewer and paper vector
                wmd_score = self.compute_wmd_score(words, best_paper_tokens)
                reviewer_paper_scores.append(wmd_score)

        if len(reviewer_paper_scores) == 0:
            return 0
        else:
            return max(reviewer_paper_scores)

	def compute_cosine_between_reviewer_paper(self, reviewer_vec, paper_vec):
	    """ 
	    Returns the cosine similarity between the reviewer vector representation 
	    and a paper vector representation 
	    """

	    return cosine_similarity(reviewer_vec.reshape(1, -1), paper_vec.reshape(1, -1))[0][0]

	def infer_new_document(self, doc):
		""" Infer a document vector for a new unseen document """

		start_alpha = .01
		infer_epoch = 1000
		vec = self.model.infer_vector(doc.split(), alpha=start_alpha, steps=infer_epoch)
		return vec

	def __tokenize_paper(self, paper):
        """ 
        Tokenizes a document
        
        Arguments:
              paper: a document represented by a string
              
        Returns:
                a list of tokens 
        """
        words = preprocess_documents.tokenize(paper)
        return words	

			