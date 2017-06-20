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
import re
import pickle
import time

        
class Model(base_model.Model):
    """
    Implementation of Top-N-Words Model (underlying w2v model)
    The model gathers the top n words from a reviewer's archive using tf-idf 
    and averages those top n word vectors to form a single averaged vector 
    representing the reviewer. The paper is represented is by averaging all word vectors in the document.
    To generate a score between a reviewer and a paper, cosine similarity is applied 
    to both the reviewer's vector and the paper's vector
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

        training_corpus = [] # need to use this corpus to get the best words on the training papers
        self.testing_corpus = [] # need to use this corpus to get best words on the test papers

        for record in archive_data:
            if record["content"]["archive"]:
                paper = self.__tokenize_paper(record["content"]["archive"])
                if(len(paper) > 0):
                    reviewer_to_papers[record["reviewer_id"]].append(paper)
                    training_corpus.append(paper)

        for paper in train_data:
            if paper['content']['archive']:
                paper_doc = self.__tokenize_paper(paper["content"]["archive"])
                self.testing_corpus.append(paper_doc) 

        self.reviewers = reviewer_to_papers.keys() # maintain a list of reviewer id's

        training_corpus = [" ".join(doc) for doc in training_corpus]
        self.testing_corpus = [" ".join(doc) for doc in self.testing_corpus]

        self.keyphrase_extractor.train_tf_idf_on_corpus(training_corpus)

        print("Building reviewer_to_vec dict...")
        self.reviewer_to_vec = defaultdict(list)
        for reviewer_id, papers in reviewer_to_papers.iteritems():
            for paper in papers:
                # reviewer_top_n_words_for_paper = paper  #use all of the words in the title to represent 'top words' for the document
                reviewer_top_n_words_for_paper = self.keyphrase_extractor.extract(paper, 5, training_corpus)
                reviewer_paper_vec = self.__build_averaged_word_vectors(reviewer_top_n_words_for_paper)
                self.reviewer_to_vec[reviewer_id].append((reviewer_top_n_words_for_paper, reviewer_paper_vec))

        return self

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
            elif self.scoring_mechanism == "word_movers":
                # compute the word movers distance between reviewer and paper vector
                print("Computing the word_movers distance between the vectors")

        if len(reviewer_paper_scores) == 0:
            return 0
        else:
            return np.mean(reviewer_paper_scores)

    def compute_max_score(self, signature, note_record):
        """ Take the max score between the paper vector and the reviewer document vectors """

        self.keyphrase_extractor.train_tf_idf_on_corpus(self.testing_corpus)

        paper_tokens = self.__tokenize_paper(note_record["content"]["archive"])
        best_paper_tokens = self.keyphrase_extractor.extract(paper_tokens, 10)
        paper_vector = self.__build_averaged_word_vectors(best_paper_tokens)
        
        reviewer_paper_scores = []

        for words, reviewer_paper_vec in self.reviewer_to_vec[signature]:
            if self.scoring_mechanism == "cosine_similarity":
                # compute the cosine similarity between reviewer vector and paper vector
                if reviewer_paper_vec.size > 1: # because the reviewer paper vector is empty (nan), the words in the paper don't have word vectors
                    reviewer_paper_score = self.compute_cosine_between_reviewer_paper(reviewer_paper_vec, paper_vector)
                    reviewer_paper_scores.append(reviewer_paper_score)

            elif self.scoring_mechanism == "word_movers":
                # compute the word movers distance between reviewer and paper vector
                print("Computing the word_movers distnace between two vectors")
        if len(reviewer_paper_scores) == 0:
            return 0
        else:
            return max(reviewer_paper_scores)

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
                continue  # skip all the words not in the vocabulary of the
        return np.sum(np.array(document_avg_vec), axis=0) / float(len(document_avg_vec))

    def __top_n_words(self, documents, corpus):
        """
        Returns a list of the top n words from a list of papers using TF-IDF weighting

        Arguments:
            papers: a list of papers
        Returns:
            a list of top words
        """

        tf_idf_weights = self.__tf_idf(documents, corpus)
        c = Counter(tf_idf_weights)
        top_n_words = c.most_common(self.top_n)
        return [word[0] for word in top_n_words]

    def __tf_idf(self, document, corpus):
        """
        Perform TF-IDF on the corpus and get back tfidf scores on the document

        Arguments:
            documents: the collection of documents to score
            corpus: the collection of all documents representing the corpus
        Returns:
            a dictionary of terms with the tf-idf weights {term => tf-idf weight}
        """

        dictionary = corpora.Dictionary(corpus)
        corpus_bow = [dictionary.doc2bow(document) for document in corpus]
        doc = dictionary.doc2bow(document)
        tfidf = TfidfModel(corpus_bow)
        corpus_tfidf = tfidf[doc]
        d = {dictionary.get(term[0]): term[1] for term in corpus_tfidf}
        return d

    def __tokenize_paper(self, paper):
        """ 
        Tokenizes a document
        
        Arguments:
              paper: a document represented by a string
              
        Returns:
                a list of tokens 
        """

        space_regexp = re.compile('[^a-zA-Z]')
        words = re.split(space_regexp, paper)
        words = filter(lambda x: len(x) > 0, words)
        words = [word.lower() for word in words]
        words = preprocess_documents.stop_word_removal(words)
        return words
