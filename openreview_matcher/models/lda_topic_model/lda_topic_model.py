from __future__ import division
from collections import defaultdict
from operator import itemgetter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from gensim.models import LdaModel
from gensim import corpora
from openreview_matcher.models import base_model
# from openreview_matcher.pre import *


class Model(base_model.Model):
    """ 
    Implementation of LDA based expertise model 
    We train an LDA model on both reviewer archives and submission papers.
    Both the author and the paper are represented by some topic vector 
    We can then compute an expertise score between a reviewer and a paper by 
    computing the cosine similarity between the two topic vectors
    """

    def __init__(self, params=None):
        self.num_topics = params["num_topics"]
        self.learning_iterations = params["learning_iterations"]
        self.reviewers = None
        self.dictionary = None
        self.corpus_bow = None
        self.lda_model = None
        self.reviewer_to_lda_vector = None

    def fit(self, train_data, archive_data):
        """
        Fits the LDA topic model on the reviewer archive and the test papers
        Caches a dictionary of reviewer lda vectors for prediction 

        Arguments
            @train_data: a list of records containing training documents
            @reviewer_archive: an iterator over records that contains the reviewer's archive

        Returns
            None
        """

        # convert archive data into a a dictionary of {reviewer_id => list of papers}
        reviewer_to_papers = defaultdict(list)

        for record in archive_data:
            if record["content"]["archive"]:
                reviewer_to_papers[record["reviewer_id"]].append(record["content"]["archive"])

        # get all of the training data (reviewer archive + submission papers)
        # assume that train_data = submission papers

        corpus = []

        for paper in train_data:
            if paper['content']['archive']:
                corpus.append(paper['content']['archive'])

        for signature, papers in reviewer_to_papers.iteritems():
            corpus.extend(papers)

        self.reviewers = reviewer_to_papers.keys() # maintain a list of reviewer id's

        corpus = [[word for word in document.lower().split()]
                for document in corpus]

        self.dictionary = corpora.Dictionary(corpus)
        self.corpus_bow = [self.dictionary.doc2bow(doc) for doc in corpus]

        print("Training LDA Model...")
        self.lda_model = LdaModel(corpus=self.corpus_bow, id2word=self.dictionary, num_topics=self.num_topics,
                                  update_every=1, chunksize=830, passes=self.learning_iteartions)

        print("Creating Reviewer Topic Vectors...")
        self.reviewer_to_lda_vector = self.___build_reviewer_lda_vector(dict(reviewer_to_papers))

        return self

    def predict(self, test_record):
        """ 
        Given a new test record (submission file), computes the expertise scores between every reviewer and this new record
            
        Argument: 
            test_record: 
        """

        paper_to_reviewer_scores = []

        for reviewer in self.reviewers:
            expertise_score = self.score(reviewer, test_record)
            paper_to_reviewer_scores.append((reviewer, expertise_score))

        ranked_reviewer_list = [reviewer_scores[0] for reviewer_scores in sorted(paper_to_reviewer_scores, key=itemgetter(1))]
        return ranked_reviewer_list

    def score(self, signature, note_record):
        """ 
        Returns an expertise score between a reviewer and a paper
        Computes the averaged topic vector for the reviewer and the topic vector for the paper
        Then using cosine similarity on both vectors to create a score representing the similarity 
        between the reviewer and the paper
        
        Arguments:
            signature: reviewer_id
            note_record: a dict representing a note (paper)
        
        Returns:
            A float representing the score
        """

        forum_content = note_record["content"]["archive"]
        reviewer_lda_vec = self.reviewer_to_lda_vector[signature]
        paper_lda_vec = self.__build_lda_topic_vector(forum_content)

        return cosine_similarity(reviewer_lda_vec, paper_lda_vec)

    def __build_lda_topic_vector(self, document):
        """ 
        Uses the trained LDA model to compute a topic vector a single document 
        
        Arguments:
            document: string representation of a document
        
        Returns:
            A numpy vector representing the topic distribution in the document
        """

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
        """ 
        
        For each reviewer this method computers a topic vector for that reviewer based on the topic 
        distributions represented in that reviewer's archive. 
        
        A reviewer's topic vector is computed by averaging individual topic vector for each paper in the reviewer's
        archive
        
        Arguments:
            reviewers: a dictionary of reviewers and their papers
        
        Returns:
            A dictionary of average reviewer lda vectors
            {reviewer_id => numpy vector}
        """

        reviewer_to_lda_vector = {}
        for reviewer, papers in reviewers.iteritems():
            reviewer_matrix = np.vstack(map(lambda doc: self.__build_lda_topic_vector(doc), papers))
            reviewer_to_lda_vector[reviewer] = np.mean(reviewer_matrix, axis=0)
        return reviewer_to_lda_vector
