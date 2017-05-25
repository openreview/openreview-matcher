from __future__ import division
from sklearn.feature_extraction.text import CountVectorizer
from collections import defaultdict
from operator import itemgetter
import numpy as np
from openreview_matcher.models import base_model


class Model(base_model.Model):
    """ Implementation of Bag of Words with Dirichlet Smooth """

    def __init__(self, params=None):
        self.corpus_metadata = {}
        self.reviewer_metadata = defaultdict(dict)

    def fit(self, train_data, archive_data):
        """
        Fits the BoW model on a corpus of training data by creating a bag of words representation for the corpus

        Arguments:
            @training_papers: a list of training documents
            @reviewer_archive_archive: an iterator over records that contains the reviewer's archive

        Returns: None
        """

        # Create a BOW representation for the corpus
        bow_corpus = CountVectorizer(lowercase=True)
        dtm_corpus = bow_corpus.fit_transform([paper['content']['archive'] for paper in train_data]).toarray()

        self.corpus_metadata["total_words"] = sum(dtm_corpus[0])
        self.corpus_metadata["bow"] = dict(zip(bow_corpus.get_feature_names(), np.asarray(dtm_corpus.sum(axis=0)).ravel()))

        # Build a BOW for each reviewer using their archive of papers
        reviewer_to_papers = defaultdict(list)
        for record in archive_data:
            if record["content"]['archive']:
                reviewer_to_papers[record["reviewer_id"]].append(record["content"]['archive'])

        self.reviewer_metadata["names"] = reviewer_to_papers.keys()

        for reviewer_name, papers in reviewer_to_papers.iteritems():
            bow_reviewer = CountVectorizer(lowercase=True)
            dtm_reviewer = bow_reviewer.fit_transform(papers).toarray()
            self.reviewer_metadata[reviewer_name]["total_words"] = sum(dtm_reviewer[0])
            reviewer_cached_word_freq = dict(zip(bow_reviewer.get_feature_names(), np.asarray(dtm_reviewer.sum(axis=0)).ravel()))
            self.reviewer_metadata[reviewer_name]["bow"] = reviewer_cached_word_freq

        return self

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

        ranked_reviewer_list = [reviewer_scores[0] for reviewer_scores in sorted(paper_to_reviewer_scores,
                                                                                 key=itemgetter(1))]
        return ranked_reviewer_list

    def score(self, signature, note_record):
        """ 
        Computes an expertise score between a reviewer and a paper
        
        Arguments
            signature: reviewer_id
            forum: paper_id
            
        Returns
            An expertise score (float) between a reviewer and paper
        """

        forum_content = note_record["content"]["archive"]
        bow_paper = CountVectorizer()
        bow_paper.fit((forum_content,))
        vocab_paper = np.array(bow_paper.get_feature_names())
        P = len(forum_content.split())
        Nar = self.reviewer_metadata[signature]["total_words"]  # total number of words in reviewer's archive
        mu = 1  # smoothing parameter
        N = self.corpus_metadata["total_words"]  # total number of words in the corpus
        score = 0
        for word in vocab_paper:

            # set default values for wAr and w is "word" is not in the dictionary
            if word not in self.reviewer_metadata[signature]["bow"]:
                wAr = 0
            else:
                wAr = self.reviewer_metadata[signature]["bow"][word]

            if word not in self.corpus_metadata["bow"]:
                w = 1
            else:
                w = self.corpus_metadata["bow"][word]

            score += self.__compute_dirichlet_smooth(Nar, mu, wAr, w, N)

        score = np.exp(score / float(P))

        return score

    def __compute_dirichlet_smooth(self, Nar, mu, wAr, w, N):
        """
        Computes the dirichlet smooth

        Arguments:
            Nar: total number of words in a reviewer's archive
            mu: smoothing parameter
            wAr: number of times a word occurs in a reviewer's archive
            w: number of times a word occurs in the corpus
            N: total number of words in the corpus

        Returns:
            A score between a reviewer's archive and a single paper
        """

        inside = ((Nar / (Nar + mu)) * (wAr / Nar) + (mu / (Nar + mu)) * (w / N))
        return np.log10(inside)
