from __future__ import division
from collections import defaultdict
from operator import itemgetter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from gensim.models import LdaModel
from gensim import corpora
from openreview_matcher.models import base_model
from openreview_matcher.preprocessors import preprocess_documents
from openreview_matcher import eval_utils
import re
import pickle

class Model(base_model.Model):
    """ 
    Implementation of LDA based expertise model 
    Train an LDA model on both reviewer archives and submission papers.
    Both the author and the paper are represented by some topic vector 
    We can then compute an expertise score between a reviewer and a paper by 
    computing the cosine similarity between the two topic vectors
    """

    def __init__(self, combinining_mechanism, scoring_mechanism, keyphrase_extractor, params=None):
        self.combining_mechanism = combinining_mechanism 
        self.scoring_mechanism = scoring_mechanism
        self.keyphrase_extractor =keyphrase_extractor 
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
                paper = " ".join(self.__tokenize_paper(record["content"]["archive"]))
                reviewer_to_papers[record["reviewer_id"]].append(paper)

        # get all of the training data (reviewer archive + submission papers)
        # assume that train_data = submission papers

        corpus = []

        for paper in train_data:
            if paper['content']['archive']:
                paper_doc = " ".join(self.__tokenize_paper(paper["content"]["archive"]))
                corpus.append(paper_doc)

        for signature, papers in reviewer_to_papers.iteritems():
            corpus.extend(papers)

        print("Number of docs in the corpus: ", len(corpus))

        self.reviewers = reviewer_to_papers.keys() # maintain a list of reviewer id's

        corpus = [[word for word in document.split()]
                for document in corpus]

        self.dictionary = corpora.Dictionary(corpus)
        self.corpus_bow = [self.dictionary.doc2bow(doc) for doc in corpus]

        if not self.lda_model:

            print("Saving the dictionary...")
            self.dictionary.save("./saved_internal_models/lda/lda_model_dictionary")

            print("Saving the corpus bow...")
            with open("./saved_internal_models/lda/corpus_bow.pkl", "w") as f:
                pickle.dump(self.corpus_bow, f)

            print("Training LDA Model...")
            self.lda_model = LdaModel(corpus=self.corpus_bow, id2word=self.dictionary, num_topics=self.num_topics,
                                      update_every=1, chunksize=830, passes=self.learning_iterations)
            self.lda_model.save("./saved_internal_models/lda/ldamodel.model")

        print("Loading in the LDA Model")

        print("Creating Reviewer Topic Vectors...")
        self.reviewer_to_lda_vector = {}
        for reviewer in self.reviewers:
            reviewer_lda_vectors = self.___build_reviewer_lda_vector(reviewer_to_papers[reviewer])
            self.reviewer_to_lda_vector[reviewer] = reviewer_lda_vectors

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

        sorted_reviewer_scores = sorted(paper_to_reviewer_scores, key=itemgetter(1), reverse=True)
        ranked_reviewer_list = ["{0};{1}".format(reviewer_scores[0].encode('utf-8'), reviewer_scores[1]) for
                                reviewer_scores in sorted_reviewer_scores]

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

        if self.combining_mechanism == "max":
            # compute the max score
            return self.compute_max_score(signature, note_record)

        elif self.combining_mechanism == "avg":
            # compute the avg score
            return self.compute_avg_score(signature, note_record)        

    def compute_cosine_between_reviewer_paper(self, reviewer_vec, paper_vec):
        """ 
        Returns the cosine similarity between the reviewer vector representation 
        and a paper vector representation 
        """

        return cosine_similarity(reviewer_vec.reshape(1, -1), paper_vec.reshape(1, -1))[0][0]

    def compute_prob_dist_between_vecs(self, reviewer_vec, paper_vec):
        """ 
        Computes the min distance to travel to match reviewer_vec and 
        paper vec using Haw-Shaun's loss function 
        """

        pass

    def compute_avg_score(self, signature, note_record):
        forum_content = " ".join(self.__tokenize_paper(note_record["content"]["archive"]))
        paper_topic_vec = self.__build_lda_topic_vector(forum_content)
        reviewer_paper_scores = [] 

        for reviewer_topic_vec in self.reviewer_to_lda_vector[signature]:
            if scoring_mechanism == "cosine_similarity":
                if reviewer_topic_vec.size > 1:
                    reviewer_paper_score = self.compute_cosine_between_reviewer_paper(reviewer_topic_vec, paper_topic_vec)
                    reviewer_paper_scores.append(reviewer_paper_score)
            elif scoring_mechanism == "word_movers":
                # compute the word movers distance between the two topic vectors
                print("Computing the word mover's distance between topic vectors")

        if len(reviewer_paper_scores) == 0:
            return 0
        else:
            return np.mean(reviewer_paper_scores)

    def compute_max_score(self, signature, note_record):
        """ 
        Compute the max score between the paper 
        and all of the papers of the reviewer 
        """ 

        forum_content = " ".join(self.__tokenize_paper(note_record["content"]["archive"]))
        paper_topic_vec = self.__build_lda_topic_vector(forum_content)
        reviewer_paper_scores = [] 

        for reviewer_topic_vec in self.reviewer_to_lda_vector[signature]:
            if self.scoring_mechanism == "cosine_similarity":
                if reviewer_topic_vec.size > 1:
                    reviewer_paper_score = self.compute_cosine_between_reviewer_paper(reviewer_topic_vec, paper_topic_vec)
                    reviewer_paper_scores.append(reviewer_paper_score)
            elif self.scoring_mechanism == "word_movers":
                # compute the word movers distance between the two topic vectors
                print("Computing the word mover's distance between topic vectors")

        if len(reviewer_paper_scores) == 0:
            return 0
        else:
            return max(reviewer_paper_scores)

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
        lda_raw_topic_distribution = dict(self.lda_model[self.dictionary.doc2bow(document.split())])
        for topic_num in num_topics:
            if topic_num not in lda_raw_topic_distribution:
                topic_vec.append(0.0)
            else:
                topic_vec.append(lda_raw_topic_distribution[topic_num])
        return np.asarray(topic_vec)

    def ___build_reviewer_lda_vector(self, reviewer_documents):
        """ 
        
        For each reviewer this method computes a topic vector for that reviewer based on the topic 
        distributions represented in that reviewer's archive. 
        
        A reviewer's topic vector is computed by averaging individual topic vector for each paper in the reviewer's
        archive
        
        Arguments:
            reviewers: a dictionary of reviewers and their papers
        
        Returns:
            A dictionary of average reviewer lda vectors
            {reviewer_id => numpy vector}
        """

        reviewer_to_lda_vector = []
        for reviewer_doc in reviewer_documents:
            paper_topic_vector = self.__build_lda_topic_vector(reviewer_doc)
            reviewer_to_lda_vector.append(paper_topic_vector)
        return reviewer_to_lda_vector

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
