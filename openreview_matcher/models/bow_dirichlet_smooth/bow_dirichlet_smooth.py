from __future__ import division
from sklearn.feature_extraction.text import CountVectorizer
from collections import defaultdict
from operator import itemgetter
import numpy as np
from openreview_matcher.models import base_model
from openreview_matcher.preprocessors import preprocess_documents
import re
import time


class Model(base_model.Model):
    """ 
    Implementation of Bag of Words with Dirichlet Smooth 
    We represent both the reviewer's archive and the submission paper as a BoW vector

    We can the use a simple language model with dirichlet smoothing to generate a score 
    between the reviewer's BoW and the paper's BoW
    
    There are two version of the model:
        concatenated_document (avg): score model using concatenated reviewer documents
        max_document: score model against all papers of the reviewer and use the max score as the paper-reviewer expertise score
        softmax: take the softmax of the reviewer document scores
    """

    def __init__(self, combinining_mechanism, scoring_mechanism, params=None):
        self.smoothing_parameter = params["mu"] # internal parameter to the actual model
        self.combinining_mechanism = combinining_mechanism  # options are: max, avg, logexpsum
        self.scoring_mechanism = scoring_mechanism
        self.corpus_metadata = {}
        self.reviewer_metadata = defaultdict(dict)

        print("Using {0} and {1}".format(self.combinining_mechanism, self.scoring_mechanism))

    def fit(self, train_data, archive_data):
        """
        Fits the BoW model on a corpus of training data by creating a BoW representation for the corpus
        Caches BoW for each reviewer into a dictionary for prediction
        
        Arguments:
            @train_data: a list of training documents
            @archive_data: an iterator over records that contains the reviewer's archive

        Returns: self
        """
        
        self.corpus_metadata = self.build_corpus_metadata(train_data)
        self.reviewer_metadata = self.build_reviewer_metadata(archive_data)

        return self

    def build_reviewer_metadata(self, archive_data):
        """ 
        Builds the reviewer metadata which essentially builds BoW representations for 
        reviewer documents 
        """

        reviewer_metadata = defaultdict(list)
        reviewer_to_papers = defaultdict(list)

        # build the reviewer_archive 
        for record in archive_data:
            if record["content"]['archive']:
                reviewer_to_papers[record["reviewer_id"]].append(record["content"]['archive'])

        reviewer_metadata["names"] = reviewer_to_papers.keys()

        if self.combinining_mechanism == "max":
            # for every reviewer and for all of their papers, build a BoW R reviewer and n documents ==> R * n
            for reviewer_name, papers in reviewer_to_papers.iteritems():
                for paper in papers:  # for each of the reviewer's paper, build a bow
                    paper_bow_representation = self.get_bow_representation(paper)
                    reviewer_metadata[reviewer_name].append(paper_bow_representation)

        elif self.combinining_mechanism == "avg":
            # for every reviewer, concatenate their papers and build a BoW for that concatenated archive ==> R
            for reviewer_name, papers in reviewer_to_papers.iteritems():
                reviewer_bow = self.get_bow_representation(" ".join(papers))
                reviewer_metadata[reviewer_name] = reviewer_bow

        return reviewer_metadata

    def build_corpus_metadata(self, train_data):
        """ 
        Builds the corpus metadata, such as the the total number of words in corpus and the BoW, 
        using the training data 
        
        Returns:
            A dictionary containing corpus metadata
            This metadata includes the total number of words in the corpus 
            and actual bow representation of the corpus
        """

        corpus = " ".join([paper['content']['archive'] for paper in train_data])
        return self.get_bow_representation(corpus, normalize=False)

    def get_bow_representation(self, paper, normalize=True):
        """ 
        Returns metadata regarding a single paper. This includes the total number of words in the document
        and the BoW representation of the document
        """

        paper_representation = {}
        bow_paper = CountVectorizer(lowercase=True, analyzer="word", tokenizer=self.__tokenize_paper)
        dtm_paper = bow_paper.fit_transform((paper,)).toarray()
        total_words_in_archive = len(self.__tokenize_paper(paper))
        cached_bow = dict(zip(bow_paper.get_feature_names(), np.asarray(dtm_paper.sum(axis=0)).ravel()))

        # normalize the word counts (TPMS)
        if normalize:
            cached_bow = {word: count/float(total_words_in_archive) for word, count in cached_bow.iteritems()}

        paper_representation["total_words"] = total_words_in_archive
        paper_representation["bow"] = cached_bow
        return paper_representation

    def predict(self, note_record):
        """
        Uses the trained BoW model to predict on reviewer expertise scores with test papers

        Arguments
            @note_record: a single test record containing forum_id

        Returns
            a list of reviewer IDs in descending order of expertise score
        """

        paper_to_reviewer_scores = []  # a list of tuples containing reviewer expertise scores (reviewer_id, score)
        for reviewer in self.reviewer_metadata["names"]:
            reviewer_paper_expertise_score = self.score(reviewer, note_record)
            paper_to_reviewer_scores.append((reviewer, reviewer_paper_expertise_score))

        sorted_reviewer_scores = sorted(paper_to_reviewer_scores, key=itemgetter(1), reverse=True)
        ranked_reviewer_list = ["{0};{1}".format(reviewer_scores[0].encode('utf-8'),reviewer_scores[1]) for
                                reviewer_scores in sorted_reviewer_scores]
        return ranked_reviewer_list

    def score(self, signature, note_record):
        """ Returns an affinity score between a reviewer and a paper """
        if self.combinining_mechanism == "max":
            return self.compute_max(signature, note_record)
        elif self.combinining_mechanism == "avg":
            return self.compute_avg(signature, note_record)
        elif self.combinining_mechanism == "logexpsum":
            return self.compute_logexpsum(signature, note_record)
        else:
            return 0.0

    def compute_avg(self, signature, note_record):
        """ 
        Computes an expertise score between a reviewer and a paper
        
        Arguments:
            signature: reviewer_id
            note_record: a dict representing a note (paper)
            
        Returns:
            An expertise score (float) between a reviewer and paper
        """

        forum_content = note_record["content"]["archive"]
        paper_tokens = self.__tokenize_paper(forum_content)
        score = self.compute_lm_score(self.reviewer_metadata[signature], paper_tokens)
        return score

    def compute_max(self, signature, note_record):
        """ Use the max scoring mechanism to score a reviewer and a paper """

        forum_content = note_record["content"]["archive"]
        paper_tokens = self.__tokenize_paper(forum_content)
        paper_scores = []

        for paper_bow in self.reviewer_metadata[signature]:
            score = self.compute_lm_score(paper_bow, paper_tokens)
            paper_scores.append(score)

        if len(paper_scores) == 0:
            return 0
        else:
            return max(paper_scores)

    def compute_logexpsum(self, signature, note_record):
        """ Compute the logexpsum score between the paper and all of the reviewer documents """
        forum_content = note_record["content"]["archive"]
        paper_tokens = self.__tokenize_paper(forum_content)
        paper_scores = []

        for paper_bow in self.reviewer_metadata[signature]:
            score = self.compute_lm_score(paper_bow, paper_tokens)
            paper_scores.append(score)

        if len(paper_scores) == 0:
            return 0
        else:
            return self.logexpsum(paper_scores)

    def logexpsum(self, scores):
        """ Computes the softmax of the scores """   
        scores = np.array(scores)
        e_x = np.exp(scores - np.max(scores))
        out = e_x / e_x.sum()
        return out
 

    def compute_lm_score(self, reviewer_bow, paper_tokens):
        """ 
        Computes a score between a reviewer bag of word representation and a list of paper tokens 
        Specifically, it uses a language model to compute the score between these representations
        """

        Nar = reviewer_bow["total_words"]  # total number of words in reviewer's archive
        mu = self.smoothing_parameter
        N = self.corpus_metadata["total_words"]  # total number of words in the corpus
        score = 0
        for word in paper_tokens:
            # set default values for wAr and w is "word" is not in the dictionary
            if word not in reviewer_bow["bow"]:
                wAr = 0.0
            else:
                wAr = reviewer_bow["bow"][word]
            if word not in self.corpus_metadata["bow"]:
                w = 0.0
            else:
                w = self.corpus_metadata["bow"][word]
            score += self.__compute_dirichlet_smooth(Nar, mu, wAr, w, N)
        score = np.exp(score / float(len(paper_tokens)))
        return score

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

    def __compute_dirichlet_smooth(self, Nar, mu, wAr, w, N):
        """
        Computes the dirichlet smooth. We use the dirichlet smooth to account for rare words that may occur in a document 
        
        Arguments:
            Nar: total number of words in a reviewer's archive
            mu: smoothing parameter
            wAr: number of times a word occurs in a reviewer's archive
            w: number of times a word occurs in the corpus
            N: total number of words in the corpus

        Returns:
            A score between a reviewer's archive and a single paper
        """

        inside = (((Nar / float(Nar + mu)) * (wAr / float(Nar))) + ((mu / float(Nar + mu)) * (w / float(N))))
        return np.log10(inside)
