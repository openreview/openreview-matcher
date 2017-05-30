import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Word2Vec, Phrases
from gensim.models.tfidfmodel import TfidfModel
from openreview_matcher.models import base_model
from gensim import corpora
from collections import Counter, defaultdict
from operator import itemgetter


class Model(base_model.Model):
    """ Implementation of Word2Vec based expertise model """
    def __init__(self, params=None):
        self.top_n = params["n_words"]
        self.w2v_model = Word2Vec.load(params["w2v_model_location"])

    def fit(self, train_data, archive_data):
        """ 
        Caches a dictionary of reviewer averaged word vectors  {reviewer_id => avg. word vector} 
        """


        # Build reviewer top_n_word_vectors
        # convert archive data into a a dictionary of {reviewer_id => list of papers}
        reviewer_to_papers = defaultdict(list)

        for record in archive_data:
            if record["content"]["archive"]:
                reviewer_to_papers[record["reviewer_id"]].append(record["content"]["archive"].lower())

        self.reviewers = reviewer_to_papers.keys() # maintain a list of reviewer id's
        corpus = []

        for paper in train_data:
            if paper['content']['archive']:
                corpus.append(paper['content']['archive'].lower())

        print("Building reviewer avg word vectors...")
        self.reviewer_to_vec = {}
        for reviewer_id, papers in reviewer_to_papers.iteritems():
            reviewer_top_n_words = self.__top_n_words(papers, corpus)
            reviewer_avg_vec = self.__build_averaged_word_vectors(reviewer_top_n_words)
            self.reviewer_to_vec[reviewer_id] = reviewer_avg_vec

        return self

    def predict(self, test_record):

        paper_to_reviewer_scores = []

        for reviewer in self.reviewers:
            expertise_score = self.score(reviewer, test_record)
            paper_to_reviewer_scores.append((reviewer, expertise_score))

        ranked_reviewer_list = [reviewer_scores[0] for reviewer_scores in
                                sorted(paper_to_reviewer_scores, key=itemgetter(1))]
        return ranked_reviewer_list

    def score(self, signature, note_record):

        reviewer_avg_vector = self.reviewer_to_vec[signature]

        paper_tokens = [token.lower() for token in note_record["content"]["archive"].split()]
        paper_avg_vector = self.__build_averaged_word_vectors(paper_tokens)

        try:
            score = cosine_similarity(reviewer_avg_vector.reshape(1, -1), paper_avg_vector.reshape(1, -1))
        except:
            score = .5
        finally:
            return score

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

    def __tf_idf(self, documents, corpus):
        """ 
        Perform TF-IDF on the corpus and get back tfidf scores on the document 
        
        Arguments:
            documents: the collection of documents to score
            corpus: the collection of all documents representing the corpus
        
        Returns:
            a dictionary of terms with the tf-idf weights {term => tf-idf weight}
        """

        corpus = [document.split() for document in corpus]
        dictionary = corpora.Dictionary(corpus)
        corpus_bow = [dictionary.doc2bow(document) for document in corpus]
        if len(documents) > 1: # a collection of documents
            doc = [dictionary.doc2bow(doc.split()) for doc in documents]
        else: # a single document to score
            doc = dictionary.doc2bow(documents[0].split())
        tfidf = TfidfModel(corpus_bow)
        corpus_tfidf = tfidf[doc]
        d = {dictionary.get(term[0]): term[1] for document in corpus_tfidf for term in document}
        return d


