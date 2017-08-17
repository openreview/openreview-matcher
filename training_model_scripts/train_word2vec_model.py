""" Train a word2vec model a collection of training documents """

import pickle
import argparse
from gensim.models import Word2Vec

def collect_training_data(training_data_location):
	""" 
	Gather all of the data needed to train the phrase model 
	
	NOTE: you can also train the phrase model on other documents. Just 
	make this method returns all of the documents you want to train on
	"""

	print "Getting training data from {0}".format(training_data_location)

	with open(training_data_location, "r") as f:
		training_data = pickle.load(f)

	return [doc.split() for doc in training_data]

def get_phrase_models(phrase_model_location):

	print "Getting phrase models from {0}".format(phrase_model_location)

	with open(phrase_model_location + "bigram_model.bin") as f:
		bigram_model = pickle.load(f)
	with open(phrase_model_location + "trigram_model.bin") as g: 
		trigram_model = pickle.load(g)

	return bigram_model, trigram_model


def apply_phrase_model_to_training_documents(training_documents, bigram_model, trigram_model):

	def trigram_transformer(words):
    """ Transform a document into a document with phrases using the learned phrase model """

	    # words = tokenize(doc)
	    bigrams = bigram_model[words]
	    trigrams = trigram_model[bigrams]
	    return trigrams

	return [trigram_transformer(doc) for doc in training_documents] # returns a list of documents where each document is encoded as a list of tokens


def train_word2vec_model(training_documents, word2vec_settings, save_location):

	print "Number of docs for training: ", len(training_documents)

	print "Example doc for training: ", training_documents[0]

	print "Starting to train word2vec model..."
	model = Word2Vec(sentencs=training_documents, min_count=5, sg=1, negative=5, sample=1e-4, **word2vec_settings)
	print "Done training word2vec model..."

	save_model(model, save_location)

def save_model(model, location):
	""" Save the word2vec model """
	
	print "Saving model to: ", location	

	model.save(location + "w2v_model.bin")



if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--data", help="location of training data (.pkl) file", required=True)
	parser.add_argument("-p", "--phrases", help="location of phrase models")
	parser.add_argument("-em", "--size", help="size of the embedding", required=True)
	parser.add_argument("-i", "--iter", help="number of iterations", required=True)
	parser.add_argument("-w", "--window", help="window size", required=True)
	parser.add_argument("-wrk", "--workers", help="number of workers", required=True)
	parser.add_argument("-s", "--save", help="location to save word2vec model")

	args = parser.parse_args()
	training_data_location = args.data	

	phrase_model_location = args.phrases

	model_embedding_size = args.size
	model_iter = args.iter
	model_window = args.window
	model_workers = args.workers

	save_location = args.save

	word2vec_params = {"window": model_window, "size": model_embedding_size, "workers": model_workers, "window": model_window}

	training_data = collect_training_data(training_data_location)
	bigram_model, trigram_model = get_phrase_models(phrase_model_location)
	training_data_with_phrases = apply_phrase_model_to_training_documents(training_data, bigram_model, trigram_model)
	train_word2vec_model(training_data_with_phrases, word2vec_params, save_location)	
