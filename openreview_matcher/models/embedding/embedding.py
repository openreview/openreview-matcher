import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Word2Vec, Phrases
from gensim.models.tfidfmodel import TfidfModel
from openreview_matcher.models import base_model
from gensim import corpora
from collections import Counter, defaultdict
from operator import itemgetter
import sys
from openreview_matcher.preprocessors import preprocess_documents
from openreview_matcher import eval_utils
import re
import pickle
import time
import random

class Model(base_model.Model):
    """
    Implementation of Word Embedding Model (underlying skipgram w2v model)
    """

    def __init__(self, combinining_mechanism, scoring_mechanism, keyphrase_extractor, params=None):
        self.combinining_mechanism = combinining_mechanism
        self.scoring_mechanism = scoring_mechanism
        self.keyphrase_extractor = keyphrase_extractor
        self.top_n = params["n_words"]
        self.w2v_model = Word2Vec.load(params["w2v_model_location"])
        self.reviewers = [] 
        self.reviewer_to_vec = None

    def fit(self, train_data, archive_data):
        """ 
        Caches a dictionary of reviewer averaged word vectors  {reviewer_id => avg. word vector} 

        Arguments:
            train_data: a list of records containing training documents
            archive_data: an iterator over records that contains reviewer archive information

        Returns:
            self
        """

        reviewer_to_papers = defaultdict(list)

        self.testing_corpus = [] 

        # maintain a dictionary of reviewer to their papers
        for record in archive_data:
            if record["content"]["archive"]:
                paper = record["content"]["archive"]
                if(len(paper) > 0):
                    reviewer_to_papers[record["reviewer_id"]].append(paper)

        self.reviewers = reviewer_to_papers.keys() # maintain a list of reviewer id's

        print("Building reviewer_to_vec dict...")

        self.reviewer_to_vec = defaultdict(list)
        for reviewer_id, papers in reviewer_to_papers.iteritems():
            for paper in papers:
                reviewer_paper_words = self.run_kp_extraction(paper, self.top_n)
                reviewer_paper_vec = self.__build_averaged_word_vectors(reviewer_paper_words) # average word embeddings for reviewer's paper
                self.reviewer_to_vec[reviewer_id].append((reviewer_paper_words, reviewer_paper_vec))
        return self

    def run_kp_extraction(self, document, n):
        """ 
        Run a kp extraction on the document. This method supports tfidf, oracle and rnn_attention 
        as methods to extract keyphrases from a individual document 

        Returns: a list tokens representing the keywords in the document
        """         

        if repr(self.keyphrase_extractor) == "tfidf":
            return self.keyphrase_extractor.extract(document, n)

        elif repr(self.keyphrase_extractor) == "oracle":
            return "oracle keyphrase extraction"

        elif repr(self.keyphrase_extractor) == "rnn_attention":
            return "rnn_attention keyphrase extraction"

        elif repr(self.keyphrase_extractor) == "no_keyword_extractor":
            return self.keyphrase_extractor.extract(document, n)

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

    def compute_cosine_between_reviewer_paper(self, reviewer_vec, paper_vec):
        """ 
        Returns the cosine similarity between the reviewer vector representation 
        and a paper vector representation 
        """

        return cosine_similarity(reviewer_vec.reshape(1, -1), paper_vec.reshape(1, -1))[0][0]

    def compute_avg_score(self, signature, note_record):
        """ Compute the avg score between the paper vector and all of the reviewer document vectors """

        self.keyphrase_extractor.train_tf_idf_on_corpus(self.testing_corpus)

        paper_tokens = self.__tokenize_paper(note_record["content"]["archive"])
        best_paper_tokens = self.keyphrase_extractor.extract(paper_tokens, 10)
        paper_vector = self.__build_averaged_word_vectors(best_paper_tokens)

        reviewer_paper_scores = []

        for words, reviewer_paper_vec in self.reviewer_to_vec[signature]:

            if self.scoring_mechanism == "cosine_similarity":
                # compute the cosine similarity between the reviewer vector and paper vectors
                if reviewer_paper_vec.size > 1:
                    reviewer_paper_score = self.compute_cosine_between_reviewer_paper(reviewer_paper_vec, paper_vector)
                    reviewer_paper_scores.append(reviewer_paper_score)
            elif self.scoring_mechanism == "wmd":
                # compute the word movers distance between reviewer and paper vector
                print("Computing the word_movers distance between the vectors")
                wmd_score = self.compute_wmd_score(words, best_paper_tokens)
                reviewer_paper_scores.append(wmd_score)

        if len(reviewer_paper_scores) == 0:
            return 0
        else:
            return np.mean(reviewer_paper_scores)

    def compute_max_score(self, signature, note_record):
        """ Take the max score between the paper vector and the reviewer document vectors """

        # self.keyphrase_extractor.train_tf_idf_on_corpus(self.testing_corpus)

        paper = " ".join(preprocess_documents.trigram_transformer(self.__tokenize_paper(note_record["content"]["abstract"])))
        
        best_paper_tokens = paper.split() # use all of the words in the query paper

        paper_vector = self.__build_averaged_word_vectors(best_paper_tokens)

        reviewer_paper_scores = []

        for words, reviewer_paper_vec in self.reviewer_to_vec[signature]:
            if self.scoring_mechanism == "cosine_similarity":
                # compute the cosine similarity between reviewer vector and paper vector

                # use this code for extracting keywords using oracle
                # top_words_from_reviewer_paper = self.get_top_keywords_from_oracle(" ".join(words), paper, 10)
                # reviewer_vec_from_top_words = self.__build_averaged_word_vectors(top_words_from_reviewer_paper)

                if reviewer_paper_vec.size > 1: # because the reviewer paper vector is empty (nan), the words in the paper don't have word vectors

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

    def compute_wmd_score(self, doc1, doc2):
        """ 
        Compute the word movers distance between two documents 
    
        Assumes that both doc1 and doc2 are a list of tokens

        """

        result = self.w2v_model.wmdistance(doc1, doc2)
        result = 1./(1.+result)  # Similarity is the negative of the distance.
        return result

    def __build_averaged_word_vectors(self, tokens):
        """
        Average all word vectors in the document

        Arguments:
            tokens: a list of tokens representing the document

        Returns:
            a numpy array
        """

        document_avg_vec = []
        for token in tokens:
            try:
                document_avg_vec.append(self.w2v_model[token])
            except:
                continue  # skip all the words not in the vocabulary of the model
        return np.sum(np.array(document_avg_vec), axis=0) / float(len(document_avg_vec))

    def keyword_extractor_using_oracle(self, a, q, n):
        """ Find the best keywords in the reviewer's paper using knowledge of the query """
        avg_q_vec = self.__build_averaged_word_vectors(q.split())
        word_scores = []
        for word in list(set(a.split())):
            if word in self.w2v_model:
                vw_word = self.w2v_model[word]
                score = cosine_similarity(vw_word.reshape(1, -1), avg_q_vec.reshape(1, -1))[0][0]
                word_scores.append((word, score))
        sorted_word_scores = sorted(word_scores, key=itemgetter(1), reverse=True)
        return [word[0] for word in sorted_word_scores[:n]]


    def keyword_extractor_using_tfidf(self, doc):
        """ Use tfidf to extract keywords from the source document """
        keywords = self.keyphrase_extractor.extract(doc, 10, None)
        return keywords
 

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

    def get_random_words_from_doc(self, doc):
        """ Choose 10 random words from a document """
        random_words = set()
        while len(random_words) != 10:
            word = random.choice(doc.split())
            random_words.add(word)
        return list(random_words)
