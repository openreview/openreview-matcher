import re
from collections import defaultdict
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from gensim.models.tfidfmodel import TfidfModel
from gensim import corpora
from operator import itemgetter

from openreview_matcher.models import base_model
from openreview_matcher.preprocessors import preprocess_documents

class Model(base_model.Model):

    def __init__(self, combinining_mechanism, scoring_mechanism, keyphrase_extractor, params=None):
        self.combinining_mechanism = combinining_mechanism
        self.scoring_mechanism = scoring_mechanism
        self.keyphrase_extractor = keyphrase_extractor
        self.reviewers = [] 
        self.reviewer_to_vec = None        

    def fit(self, train_data, archive_data):
        """
        Fit the model to the data.

        Arguments
            @train_data: an iterator over records (dicts) that contains the training data.
            Records must have a "content" field containing a string and a "forum" field
            containing the record's forum ID.

            @archive_data: an iterator over records (dicts) that contains each reviewer's
            archive. Records must have a "content" field containing a string representing
            the archive, and a "reviewer_id" field with the reviewer's OpenReview ID.

        Returns
            None

        """


        tfidf_training_corpus = [] 
        reviewer_to_papers = defaultdict(list)

        for record in archive_data:
            if record["content"]["archive"]:
                paper = record["content"]["archive"]
                reviewer_to_papers[record["reviewer_id"]].append(paper)
                tfidf_training_corpus.append(paper)

        for paper in train_data:
            if paper['content']['archive']:
                paper = " ".join(preprocess_documents.trigram_transformer(self.__tokenize_paper(paper["content"]["archive"])))
                tfidf_training_corpus.append(paper)        

        self.reviewers = reviewer_to_papers.keys() # maintain a list of reviewer id's

        print "Building Tfidf model on training documents"
        self.tfidf_model = TfidfVectorizer(max_df=.95)
        self.tfidf_model.fit(tfidf_training_corpus)

        self.reviewer_to_vec = defaultdict(list)

        for reviewer_id, papers in reviewer_to_papers.iteritems():
            for paper in papers: 
                tfidf_vector_for_paper = self.get_tfidf_vector_for_document(paper)
                print "Paper:", paper[:10], "Tfidf Vec: ", len(tfidf_vector_for_paper)
                self.reviewer_to_vec[reviewer_id].append((paper, tfidf_vector_for_paper))
        return self

    def predict(self, test_record):
        """
        predict() should return a list of openreview user IDs, in descending order by
        expertise score in relation to the test record.

        Arguments
            @test_record: a note record (dict) representing the note to rank against.

            Testing records should have a "forum" field. This means that the record
            is identified in OpenReview by the ID listed in that field.

        Returns
            a list of reviewer IDs in descending order of expertise score

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

        paper = " ".join(preprocess_documents.trigram_transformer(self.__tokenize_paper(note_record["content"]["abstract"])))
        paper_tfidf_vector = self.get_tfidf_vector_for_document(paper)

        print "Paper tfidf vector: ", len(paper_tfidf_vector)

        reviewer_paper_scores = []

        for reviewer_paper, reviewer_paper_vec in self.reviewer_to_vec[signature]:
            if self.scoring_mechanism == "cosine_similarity":

                if reviewer_paper_vec.size > 1: # because the reviewer paper vector is empty (nan), the words in the paper don't have word vectors

                    reviewer_paper_score = self.compute_cosine_between_reviewer_paper(reviewer_paper_vec, paper_tfidf_vector)
                    reviewer_paper_scores.append(reviewer_paper_score)

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

    def get_tfidf_vector_for_document(self, doc):
        output = self.tfidf_model.transform([doc]).toarray()[0]
        return output

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
